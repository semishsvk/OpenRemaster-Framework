"""M004 two-store witness *emulator*, never a production trust or dispatch authority.

Models a forward-only PREPARED -> COMMITTED external witness protocol. The
emulated witness is a second local SQLite file and uses a process-held HMAC
key; neither storage nor key is protected against host rollback/compromise.
Every result is non-authorizing. No recovered workers or game assets are used.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re
import secrets
import sqlite3

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}\Z")
_VERSION = "ORCH-M004.WitnessLab.v0"


class WitnessBlocked(ValueError):
    """Fail-closed divergence, malformed input or unresolved pending state."""


class SimulatedCrash(RuntimeError):
    """Test-only injected interruption."""


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise WitnessBlocked("invalid identifier")
    return value


def _integer(value):
    if type(value) is not int or value < 0 or value >= 2**63:
        raise WitnessBlocked("invalid monotonic integer")
    return value


def canonical_json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise WitnessBlocked("invalid canonical JSON") from exc


def digest(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _owner_state(state):
    required = {"schema", "store_revision", "owner_epoch", "status", "job_id",
                "owner_id", "attempt_id", "expires_utc"}
    if type(state) is not dict or set(state) != required:
        raise WitnessBlocked("invalid owner state shape")
    if state["schema"] != "ORCH-M002.Structural.v0.OwnerSnapshot":
        raise WitnessBlocked("incompatible owner state version")
    _integer(state["store_revision"])
    _integer(state["owner_epoch"])
    if state["status"] not in ("ACTIVE", "FREE"):
        raise WitnessBlocked("invalid owner status")
    if state["status"] == "FREE":
        if any(state[k] is not None for k in ("job_id", "owner_id", "attempt_id", "expires_utc")):
            raise WitnessBlocked("free state retains ownership")
    else:
        for field in ("job_id", "owner_id", "attempt_id"):
            _id(state[field])
        if not isinstance(state["expires_utc"], str) or not state["expires_utc"].endswith("Z"):
            raise WitnessBlocked("invalid owner expiry")
    return state


class WitnessEmulator:
    """A separate SQLite *simulation*, not an independent trust anchor."""

    def __init__(self, file_path, *, test_key=None):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # In-memory test-only key: not persisted, rotated or hardware-protected.
        key = secrets.token_bytes(32) if test_key is None else test_key
        if type(key) is not bytes or len(key) < 32:
            raise WitnessBlocked("test MAC key must contain 32+ bytes")
        self.__key = key

    def _connect(self):
        conn = sqlite3.connect(self.path, isolation_level=None, timeout=5.0)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _seal(self, payload):
        return hmac.new(self.__key, canonical_json(payload).encode("utf-8"),
                        hashlib.sha256).hexdigest()

    def _ticket(self, pending):
        return {"payload": pending, "mac_sha256": self._seal(pending)}

    def _stable_mac(self, namespace, revision, epoch, state_sha256):
        return self._seal({"version": _VERSION, "namespace": namespace,
                           "revision": revision, "epoch": epoch,
                           "state_sha256": state_sha256})

    def _verify_ticket(self, ticket):
        if (type(ticket) is not dict or set(ticket) != {"payload", "mac_sha256"}
                or type(ticket["payload"]) is not dict
                or type(ticket["mac_sha256"]) is not str
                or not _SHA.fullmatch(ticket["mac_sha256"])):
            raise WitnessBlocked("invalid witness ticket")
        if not hmac.compare_digest(self._seal(ticket["payload"]), ticket["mac_sha256"]):
            raise WitnessBlocked("invalid ticket MAC")
        return ticket["payload"]

    def initialize(self, namespace, owner_state):
        """Once-only bootstrap; caller must authenticate initial state externally."""
        _id(namespace)
        before = _owner_state(owner_state)
        if before["store_revision"] != 0 or before["owner_epoch"] != 0 or before["status"] != "FREE":
            raise WitnessBlocked("witness bootstrap must begin at empty genesis")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                db.execute("CREATE TABLE IF NOT EXISTS witness (namespace TEXT PRIMARY KEY, revision INTEGER NOT NULL, epoch INTEGER NOT NULL, state_sha TEXT NOT NULL, state_mac TEXT NOT NULL, pending TEXT, pending_mac TEXT)")
                if db.execute("SELECT 1 FROM witness WHERE namespace=?", (namespace,)).fetchone():
                    raise WitnessBlocked("witness namespace already initialized")
                state_sha = digest(before)
                db.execute("INSERT INTO witness VALUES (?, ?, ?, ?, ?, NULL, NULL)",
                           (namespace, 0, 0, state_sha, self._stable_mac(namespace, 0, 0, state_sha)))
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return {"status": "EMULATOR_BOOTSTRAPPED_ONLY", "dispatch_authorized": False}

    def _read(self, db, namespace):
        try:
            row = db.execute("SELECT revision,epoch,state_sha,state_mac,pending,pending_mac FROM witness WHERE namespace=?", (namespace,)).fetchone()
        except sqlite3.OperationalError as exc:
            raise WitnessBlocked("witness store uninitialized") from exc
        if row is None:
            raise WitnessBlocked("witness namespace not initialized")
        rev, epoch, state_sha, state_mac, pending_json, pending_mac = row
        _integer(rev)
        _integer(epoch)
        if type(state_sha) is not str or not _SHA.fullmatch(state_sha):
            raise WitnessBlocked("corrupted witness state hash")
        if type(state_mac) is not str or not hmac.compare_digest(
                state_mac, self._stable_mac(namespace, rev, epoch, state_sha)):
            raise WitnessBlocked("witness stable-state MAC mismatch")
        if pending_json is None:
            if pending_mac is not None:
                raise WitnessBlocked("orphan pending MAC")
            pending = None
        else:
            try:
                pending = json.loads(pending_json)
            except (ValueError, TypeError) as exc:
                raise WitnessBlocked("invalid pending record") from exc
            expected_keys = {"version", "namespace", "idempotency_key", "before_revision",
                             "before_epoch", "before_sha256", "after_revision",
                             "after_epoch", "after_sha256"}
            if type(pending) is not dict or set(pending) != expected_keys:
                raise WitnessBlocked("corrupted pending shape")
            if (pending["version"] != _VERSION or pending["namespace"] != namespace
                    or type(pending_mac) is not str
                    or not hmac.compare_digest(pending_mac, self._seal(pending))):
                raise WitnessBlocked("witness pending MAC mismatch")
            _id(pending["idempotency_key"])
            for field in ("before_revision", "before_epoch", "after_revision", "after_epoch"):
                _integer(pending[field])
            for field in ("before_sha256", "after_sha256"):
                if type(pending[field]) is not str or not _SHA.fullmatch(pending[field]):
                    raise WitnessBlocked("invalid pending state identity")
            if (pending["before_revision"], pending["before_epoch"],
                    pending["before_sha256"]) != (rev, epoch, state_sha):
                raise WitnessBlocked("pending record inconsistent with stable state")
            if (pending["after_revision"] != rev + 1
                    or pending["after_epoch"] < epoch):
                raise WitnessBlocked("nonmonotonic pending successor")
        return {"namespace": namespace, "revision": rev, "epoch": epoch,
                "state_sha256": state_sha, "pending": pending}

    def snapshot(self, namespace):
        _id(namespace)
        with closing(self._connect()) as db:
            return self._read(db, namespace)

    def prepare(self, namespace, key, before, after):
        """Reserve a forward-only intent, blocking all other intents until resolved."""
        _id(namespace)
        _id(key)
        before = _owner_state(before)
        after = _owner_state(after)
        if (after["store_revision"] != before["store_revision"] + 1
                or after["owner_epoch"] < before["owner_epoch"]):
            raise WitnessBlocked("nonmonotonic target")
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                cur = self._read(db, namespace)
                if cur["pending"] is not None:
                    raise WitnessBlocked("PENDING_RECONCILIATION_REQUIRED")
                if ((cur["revision"], cur["epoch"], cur["state_sha256"])
                        != (before["store_revision"], before["owner_epoch"], digest(before))):
                    raise WitnessBlocked("STABLE_WITNESS_DIVERGENCE")
                pending = {
                    "version": _VERSION, "namespace": namespace,
                    "idempotency_key": key, "before_revision": cur["revision"],
                    "before_epoch": cur["epoch"], "before_sha256": cur["state_sha256"],
                    "after_revision": after["store_revision"],
                    "after_epoch": after["owner_epoch"], "after_sha256": digest(after),
                }
                db.execute("UPDATE witness SET pending=?,pending_mac=? WHERE namespace=? AND pending IS NULL",
                           (canonical_json(pending), self._seal(pending), namespace))
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return self._ticket(pending)

    def finalize(self, namespace, ticket, observed_owner):
        """Forward-only completion; HMAC authenticates emulator's own token only."""
        _id(namespace)
        claim = self._verify_ticket(ticket)
        state = _owner_state(observed_owner)
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                cur = self._read(db, namespace)
                if cur["pending"] != claim:
                    raise WitnessBlocked("ticket does not match current pending intent")
                if (cur["revision"] != claim["before_revision"]
                        or cur["epoch"] != claim["before_epoch"]
                        or cur["state_sha256"] != claim["before_sha256"]):
                    raise WitnessBlocked("pending witness predecessor mismatch")
                if ((state["store_revision"], state["owner_epoch"], digest(state))
                        != (claim["after_revision"], claim["after_epoch"], claim["after_sha256"])):
                    raise WitnessBlocked("DB_NOT_AT_PREPARED_TARGET")
                db.execute("UPDATE witness SET revision=?,epoch=?,state_sha=?,state_mac=?,pending=NULL,pending_mac=NULL WHERE namespace=?",
                           (claim["after_revision"], claim["after_epoch"], claim["after_sha256"],
                            self._stable_mac(namespace, claim["after_revision"], claim["after_epoch"],
                                             claim["after_sha256"]), namespace))
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return {"status": "FORWARD_COMMITTED_LAB_ONLY", "revision": state["store_revision"],
                "owner_epoch": state["owner_epoch"], "dispatch_authorized": False,
                "mac_sha256": self._seal({"namespace": namespace, "revision": state["store_revision"],
                                          "state_sha256": digest(state)})}

    def reconcile(self, namespace, owner_state):
        """Never abort a pending intent; forward only if database reached target."""
        _id(namespace)
        state = _owner_state(owner_state)
        cur = self.snapshot(namespace)
        if cur["pending"] is None:
            if (cur["revision"], cur["epoch"], cur["state_sha256"]) != (state["store_revision"], state["owner_epoch"], digest(state)):
                raise WitnessBlocked("STABLE_DB_WITNESS_DIVERGENCE")
            return {"status": "STABLE_LAB_ONLY", "dispatch_authorized": False}
        p = cur["pending"]
        actual = (state["store_revision"], state["owner_epoch"], digest(state))
        prior = (p["before_revision"], p["before_epoch"], p["before_sha256"])
        later = (p["after_revision"], p["after_epoch"], p["after_sha256"])
        if actual == prior:
            return {"status": "PENDING_WITH_OLD_DB_BLOCKED", "dispatch_authorized": False}
        if actual != later:
            raise WitnessBlocked("PENDING_DB_DIVERGENCE")
        return self.finalize(namespace, self._ticket(p), state)


class TwoStoreCoordinatorLab:
    """Demonstrates the DB->witness commit gap, never issues execution grants.

    Owner adapter must provide snapshot(namespace) and
    apply(namespace,key,proposal,witness,now=...,owner_token=...). The
    existing M003 CASLab supplies these functions. The emulator supplies
    no authorization, capacity, remote calls, or worker side effects.
    """

    def __init__(self, owner_store, witness_emulator):
        self.owner = owner_store
        self.witness = witness_emulator

    def apply(self, namespace, key, proposal, *, now, owner_token=None, failpoint=None):
        _id(namespace)
        _id(key)
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise WitnessBlocked("timezone-aware clock required")
        if failpoint not in (None, "after_prepare", "after_owner_commit", "after_witness_commit"):
            raise WitnessBlocked("invalid synthetic failpoint")
        before = self.owner.snapshot(namespace)
        status = self.witness.reconcile(namespace, before)
        if status["status"] != "STABLE_LAB_ONLY":
            raise WitnessBlocked("existing pending witness must be recovered first")
        if type(proposal) is not dict or type(proposal.get("next_state")) is not dict:
            raise WitnessBlocked("missing CAS proposal")
        ticket = self.witness.prepare(namespace, key, before, proposal["next_state"])
        if failpoint == "after_prepare":
            raise SimulatedCrash("after witness prepare, before DB CAS")
        try:
            result = self.owner.apply(namespace, key, proposal,
                                      (before["store_revision"], before["owner_epoch"]),
                                      now=now, owner_token=owner_token)
        except Exception:
            # Never automatically abandon or compensate pending witness.
            # A late previous writer could otherwise commit after reversal.
            raise
        if result.get("dispatch_authorized") is not False:
            raise WitnessBlocked("owner adapter unexpectedly authorized dispatch")
        if failpoint == "after_owner_commit":
            raise SimulatedCrash("after DB commit, before witness commit")
        finalized = self.witness.finalize(namespace, ticket, self.owner.snapshot(namespace))
        if failpoint == "after_witness_commit":
            raise SimulatedCrash("after witness commit, before client reply")
        stable = self.witness.reconcile(namespace, self.owner.snapshot(namespace))
        if stable["status"] != "STABLE_LAB_ONLY":
            raise WitnessBlocked("final consistency check failed")
        return {"status": "TWO_STORE_LAB_ONLY", "owner_result": result,
                "witness_result": finalized, "dispatch_authorized": False}

    def recover(self, namespace):
        return self.witness.reconcile(namespace, self.owner.snapshot(namespace))
