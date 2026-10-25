"""M003 isolated SQLite CAS laboratory. NEVER an admission or dispatch authority.

No network, subprocess, signing, worker execution, or game asset access.
The supplied witness is deliberately NOT authenticated by this module: only an
external trusted monotonic anchor can prevent rollback beyond the lab boundary.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3

SCHEMA = "ORCH-M002.Structural.v0.OwnerSnapshot"
KINDS = {"ACQUIRE_PROPOSAL_ONLY", "RENEW_PROPOSAL_ONLY", "RELEASE_PROPOSAL_ONLY"}
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_MAX_INT = 2**63 - 1
_STATE_KEYS = {"schema", "store_revision", "owner_epoch", "status", "job_id", "owner_id", "attempt_id", "expires_utc"}
_PROPOSAL_KEYS = {"kind", "expected_store_revision", "next_state", "requires_atomic_durable_cas"}


class Rejected(ValueError):
    """Fail-closed structural or transactional rejection."""


class InjectedCrash(RuntimeError):
    """Synthetic failpoint in disposable laboratory tests only."""


def _number(value, *, minimum=0):
    if type(value) is not int or not minimum <= value <= _MAX_INT:
        raise Rejected("invalid integer or SQLite integer overflow")
    return value


def _ident(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise Rejected("invalid identifier")
    return value


def _utc(value):
    if type(value) is not str or not value.endswith("Z"):
        raise Rejected("UTC Z timestamp required")
    try:
        d = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Rejected("invalid timestamp") from exc
    if d.utcoffset().total_seconds() != 0:
        raise Rejected("non-UTC timestamp")
    return d


def _now(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Rejected("timezone-aware clock required")
    return value.astimezone(timezone.utc)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise Rejected("invalid JSON") from exc


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _validate_state(state):
    if type(state) is not dict or set(state) != _STATE_KEYS or state["schema"] != SCHEMA:
        raise Rejected("invalid snapshot schema or keys")
    _number(state["store_revision"])
    _number(state["owner_epoch"])
    if state["status"] == "FREE":
        if any(state[k] is not None for k in ("job_id", "owner_id", "attempt_id", "expires_utc")):
            raise Rejected("FREE snapshot has owner")
    elif state["status"] == "ACTIVE":
        _number(state["owner_epoch"], minimum=1)
        for k in ("job_id", "owner_id", "attempt_id"):
            _ident(state[k])
        _utc(state["expires_utc"])
    else:
        raise Rejected("invalid status")
    return state


def _validate_owner_token(before, kind, token):
    """An unsigned test token is only a structural assertion, never identity proof."""
    if kind == "ACQUIRE_PROPOSAL_ONLY":
        if token is not None:
            raise Rejected("acquire must not claim an existing owner token")
        return
    if type(token) is not dict or set(token) != {"job_id", "owner_id", "attempt_id", "owner_epoch"}:
        raise Rejected("renew/release requires an exact owner token")
    for field in ("job_id", "owner_id", "attempt_id"):
        _ident(token[field])
    _number(token["owner_epoch"], minimum=1)
    if any(before[field] != token[field] for field in token):
        raise Rejected("STALE_OR_MISMATCHED_OWNER_TOKEN")


def _validate_transition(before, proposal, now, owner_token):
    if type(proposal) is not dict or set(proposal) != _PROPOSAL_KEYS:
        raise Rejected("invalid proposal fields")
    kind = proposal["kind"]
    if type(kind) is not str or kind not in KINDS or proposal["requires_atomic_durable_cas"] is not True:
        raise Rejected("non-CAS or unsupported proposal")
    _validate_owner_token(before, kind, owner_token)
    revision = _number(proposal["expected_store_revision"])
    if revision != before["store_revision"]:
        raise Rejected("STALE_EXPECTED_REVISION")
    after = _validate_state(proposal["next_state"])
    if after["store_revision"] != revision + 1:
        raise Rejected("revision must advance by one")
    if kind == "ACQUIRE_PROPOSAL_ONLY":
        if before["status"] == "ACTIVE" and _utc(before["expires_utc"]) > now:
            raise Rejected("ACTIVE_LEASE")
        if after["status"] != "ACTIVE" or after["owner_epoch"] != before["owner_epoch"] + 1:
            raise Rejected("acquire must increment owner epoch")
        expiry = _utc(after["expires_utc"])
        if not now < expiry <= now.replace(microsecond=0) + timedelta(seconds=60):
            raise Rejected("acquire expiry outside bounded window")
    else:
        if before["status"] != "ACTIVE" or _utc(before["expires_utc"]) <= now:
            raise Rejected("STALE_OR_EXPIRED_OWNER")
        if after["owner_epoch"] != before["owner_epoch"]:
            raise Rejected("renew/release cannot change epoch")
        if kind == "RENEW_PROPOSAL_ONLY":
            if after["status"] != "ACTIVE" or any(after[k] != before[k] for k in ("job_id", "owner_id", "attempt_id")):
                raise Rejected("renew owner mismatch")
            expiry = _utc(after["expires_utc"])
            if not _utc(before["expires_utc"]) < expiry <= now.replace(microsecond=0) + timedelta(seconds=60):
                raise Rejected("nonadvancing/out-of-bound renewal")
        elif after["status"] != "FREE" or any(after[k] is not None for k in ("job_id", "owner_id", "attempt_id", "expires_utc")):
            raise Rejected("release must clear owner")
    return after


class CASLab:
    """Per-operation SQLite transaction; no execution authority is ever returned."""

    def __init__(self, database_path):
        self.path = Path(database_path)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA journal_mode=DELETE")
        return db

    def create_namespace(self, namespace):
        _ident(namespace)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS states(namespace TEXT PRIMARY KEY, revision INTEGER NOT NULL, epoch INTEGER NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS receipts(namespace TEXT NOT NULL, idempotency_key TEXT NOT NULL, request_digest TEXT NOT NULL, result_json TEXT NOT NULL, PRIMARY KEY(namespace,idempotency_key))")
            initial = dict(schema=SCHEMA, store_revision=0, owner_epoch=0,
                           status="FREE", job_id=None, owner_id=None, attempt_id=None, expires_utc=None)
            if db.execute("SELECT 1 FROM states WHERE namespace=?", (namespace,)).fetchone():
                raise Rejected("namespace already initialized")
            db.execute("INSERT INTO states VALUES (?,?,?,?)", (namespace, 0, 0, _canonical(initial)))
        return {"status": "LAB_NAMESPACE_INITIALIZED", "dispatch_authorized": False}

    def _load(self, db, namespace):
        try:
            row = db.execute("SELECT revision,epoch,payload FROM states WHERE namespace=?", (namespace,)).fetchone()
        except sqlite3.OperationalError as exc:
            raise Rejected("namespace not initialized or SQLite schema missing") from exc
        if row is None:
            raise Rejected("namespace not initialized")
        try:
            obj = _validate_state(json.loads(row[2]))
        except (TypeError, ValueError) as exc:
            raise Rejected("corrupt persisted state") from exc
        if obj["store_revision"] != row[0] or obj["owner_epoch"] != row[1]:
            raise Rejected("inconsistent persisted state")
        return obj

    def snapshot(self, namespace):
        _ident(namespace)
        with closing(self._connect()) as db, db:
            return dict(self._load(db, namespace))

    def apply(self, namespace, key, proposal, witness, *, now, owner_token=None, failpoint=None):
        """Serialize CAS to SQLite and record idempotency receipt in one txn.

        witness=(revision,epoch) is an INJECTED assertion, not authenticated here.
        Any mismatch fails closed, including after DB commit before witness update.
        """
        _ident(namespace)
        _ident(key)
        moment = _now(now)
        if type(witness) is not tuple or len(witness) != 2:
            raise Rejected("trusted external witness missing")
        rev, epoch = (_number(witness[0]), _number(witness[1]))
        if failpoint not in (None, "before_commit", "after_commit"):
            raise Rejected("unsupported synthetic failpoint")
        request_hash = _digest({"namespace": namespace, "proposal": proposal, "owner_token": owner_token})
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            state = self._load(db, namespace)
            if (state["store_revision"], state["owner_epoch"]) != (rev, epoch):
                raise Rejected("WITNESS_DIVERGENCE_FAIL_CLOSED")
            existing = db.execute("SELECT request_digest,result_json FROM receipts WHERE namespace=? AND idempotency_key=?", (namespace, key)).fetchone()
            if existing:
                if existing[0] != request_hash:
                    raise Rejected("IDEMPOTENCY_KEY_REUSED_WITH_OTHER_REQUEST")
                result = json.loads(existing[1])
                return {**result, "status": "REPLAYED_LAB_ONLY", "dispatch_authorized": False}
            after = _validate_transition(state, proposal, moment, owner_token)
            update = db.execute("UPDATE states SET revision=?, epoch=?, payload=? WHERE namespace=? AND revision=? AND epoch=?",
                                (after["store_revision"], after["owner_epoch"], _canonical(after), namespace, rev, epoch))
            if update.rowcount != 1:
                raise Rejected("CAS_LOST_RACE")
            result = {"status": "CAS_COMMITTED_LAB_ONLY", "store_revision": after["store_revision"],
                      "owner_epoch": after["owner_epoch"], "requires_external_witness_update": True,
                      "dispatch_authorized": False, "request_digest": request_hash}
            db.execute("INSERT INTO receipts VALUES (?,?,?,?)", (namespace, key, request_hash, _canonical(result)))
            if failpoint == "before_commit":
                raise InjectedCrash("simulated crash before transaction commit")
            db.commit()
        if failpoint == "after_commit":
            raise InjectedCrash("simulated crash after commit, before caller reply")
        return result
