"""M011: signed remote-recovery receipt + atomic LOCAL evidence journal.

Research-only: never reaches remote network/owner gateway/native worker. A
signature validates signer-controlled bytes, NOT the freshness or authenticity
of a remotely current high-water, native side effects or global nonce CAS.
"""
from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
import sqlite3

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from openremaster.m005_anchor_contract import canonical_json, sha256_json
from openremaster.m010_durable_recovery import DurableReviewLedger, RecoveryHold

SCHEMA = "ORF-M011.SignedRemoteRecoveryReceipt.v1"
STORE_SCHEMA = "ORF-M011.LocalSignedRecoveryJournal.v1"
AUDIENCE = "ORF-RemoteRecovery-ReviewOnly-v1"
CONTEXT = b"OpenRemaster|M011-SignedRemoteRecovery|v1\x00"
MAX = 9223372036854775000
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}\Z")
CHALLENGE = re.compile(r"[A-Za-z0-9_-]{22,128}\Z")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
RESULTS = frozenset(("COMMITTED", "REJECTED"))
SIGNED_FIELDS = frozenset({
    "schema", "audience", "authority_id", "key_id",
    "scope", "operation_id", "probe_id", "challenge", "request_sha256",
    "prior_head_sha256", "candidate_head_sha256", "remote_head_sha256",
    "sequence", "owner_epoch", "fence_generation", "result",
    "trust_generation", "remote_operation_sha256", "m009_head_receipt_sha256",
    "issued_utc", "expires_utc", "signature_b64",
})
PROBE_FAILURE_POINTS = frozenset(("BEFORE_PROBE_COMMIT", "AFTER_PROBE_COMMIT"))
RECEIPT_FAILURE_POINTS = frozenset(("BEFORE_SIGNED_RESULT_COMMIT", "AFTER_SIGNED_RESULT_COMMIT"))


class SignedRecoveryHold(ValueError):
    """Fail closed. No code path in M011 grants execution."""


@dataclass(frozen=True)
class PinnedRecoveryTrust:
    """Caller-pinned lab view only, never a trustworthy remote CURRENT view."""
    authority_id: str
    public_keys: dict
    revoked_key_ids: frozenset
    generation: int
    expires_utc: str


def _fields(value, fields, label):
    if type(value) is not dict or set(value) != fields:
        raise SignedRecoveryHold(label + ": exact field set required")
    return value


def _name(value, label):
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        raise SignedRecoveryHold(label + ": invalid identifier")
    return value


def _sha(value, label):
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise SignedRecoveryHold(label + ": invalid SHA256")
    return value


def _counter(value, label, minimum=0):
    if type(value) is not int or not minimum <= value <= MAX:
        raise SignedRecoveryHold(label + ": invalid integer")
    return value


def _instant(value, label):
    if type(value) is not str or TIME.fullmatch(value) is None:
        raise SignedRecoveryHold(label + ": exact UTC Z-seconds required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SignedRecoveryHold(label + ": invalid calendar time") from exc


def _now(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise SignedRecoveryHold("aware verification clock required")
    return now.astimezone(timezone.utc)


def _failure(point, name):
    """Synthetic exceptions; child-only tests can replace this with os._exit."""
    if point == name:
        raise SignedRecoveryHold("injected synthetic failure: " + name)


def signing_message(receipt):
    _fields(receipt, SIGNED_FIELDS, "signed recovery receipt")
    try:
        return CONTEXT + canonical_json({k: v for k, v in receipt.items() if k != "signature_b64"})
    except (TypeError, ValueError) as exc:
        raise SignedRecoveryHold("malformed canonical signing payload") from exc


def _pin_trust(trust, now):
    if type(trust) is not PinnedRecoveryTrust:
        raise SignedRecoveryHold("caller must explicitly pin trust view")
    _name(trust.authority_id, "trust authority")
    _counter(trust.generation, "trust generation", 1)
    if type(trust.public_keys) is not dict or type(trust.revoked_key_ids) is not frozenset:
        raise SignedRecoveryHold("malformed trusted key/revocation view")
    public = {}
    for key_id, raw in trust.public_keys.items():
        _name(key_id, "key identifier")
        if type(raw) is not bytes or len(raw) != 32:
            raise SignedRecoveryHold("malformed pinned Ed25519 public key")
        public[key_id] = bytes(raw)
    revoked = frozenset(_name(key_id, "revoked key id") for key_id in trust.revoked_key_ids)
    if _now(now) >= _instant(trust.expires_utc, "trust expiry"):
        raise SignedRecoveryHold("trust view expired")
    return PinnedRecoveryTrust(trust.authority_id, public, revoked, trust.generation, trust.expires_utc)


def verify_signed_recovery_receipt(*, receipt, trust, expected_authority, now):
    """Verify detached Ed25519 review claim only; no external-current guarantee."""
    row = deepcopy(receipt)
    _fields(row, SIGNED_FIELDS, "signed recovery receipt")
    if row["schema"] != SCHEMA or row["audience"] != AUDIENCE:
        raise SignedRecoveryHold("wrong signed recovery version or audience")
    for field in ("authority_id","key_id","scope","operation_id","probe_id"):
        _name(row[field], field)
    for field in ("request_sha256","prior_head_sha256","candidate_head_sha256",
                  "remote_head_sha256","remote_operation_sha256","m009_head_receipt_sha256"):
        _sha(row[field], field)
    if type(row["challenge"]) is not str or CHALLENGE.fullmatch(row["challenge"]) is None:
        raise SignedRecoveryHold("malformed recovery challenge")
    for field in ("sequence","owner_epoch","fence_generation","trust_generation"):
        _counter(row[field], field, 1)
    if row["result"] not in RESULTS:
        raise SignedRecoveryHold("only exact COMMITTED/REJECTED outcomes may be signed")
    if (row["remote_head_sha256"] !=
        (row["candidate_head_sha256"] if row["result"] == "COMMITTED"
         else row["prior_head_sha256"])):
        raise SignedRecoveryHold("signed remote resulting head disagrees with outcome")
    current = _now(now)
    issued = _instant(row["issued_utc"], "issued")
    expires = _instant(row["expires_utc"], "expires")
    if not (issued <= current < expires and timedelta(0) < expires-issued <= timedelta(seconds=45)):
        raise SignedRecoveryHold("stale/future/excessive signed recovery window")
    pinned = _pin_trust(trust, current)
    _name(expected_authority, "expected authority")
    if row["authority_id"] != expected_authority or pinned.authority_id != expected_authority:
        raise SignedRecoveryHold("wrong attesting authority")
    if row["trust_generation"] != pinned.generation:
        raise SignedRecoveryHold("current trust generation not pinned")
    if row["key_id"] in pinned.revoked_key_ids:
        raise SignedRecoveryHold("recovery signer revoked in pinned view")
    public = pinned.public_keys.get(row["key_id"])
    if type(public) is not bytes or len(public) != 32:
        raise SignedRecoveryHold("unknown recovery signer")
    sig = row["signature_b64"]
    if type(sig) is not str or len(sig) > 128:
        raise SignedRecoveryHold("invalid signature field")
    try:
        binary = base64.b64decode(sig, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SignedRecoveryHold("invalid recovery signature encoding") from exc
    if len(binary) != 64 or base64.b64encode(binary).decode("ascii") != sig:
        raise SignedRecoveryHold("noncanonical Ed25519 signature")
    try:
        Ed25519PublicKey.from_public_bytes(public).verify(binary, signing_message(row))
    except (InvalidSignature, ValueError) as exc:
        raise SignedRecoveryHold("recovery signature invalid") from exc
    return {
        "status": "SIGNED_RECOVERY_CLAIM_REVIEW_ONLY",
        "verified_receipt_copy": row,
        "receipt_sha256": sha256_json(row),
        "pinned_trust_copy": pinned,
        "receipt_signature_valid": True,
        "external_current_head_verified": False,
        "remote_nonce_consumption_verified": False,
        "native_worker_dispatch_authorized": False,
    }


class SignedRecoveryJournal:
    """M010 SAME-transaction signed receipt recording in an isolated SQLite DB.

    This is diagnostic consistency, not cross-host authority. A privileged
    whole-file rollback restores old valid rows and remains undetectable.
    """
    def __init__(self, directory):
        self.ledger = DurableReviewLedger(directory)
        self.db = self.ledger.db
        self.db.execute("""CREATE TABLE IF NOT EXISTS m011_meta
                         (k TEXT PRIMARY KEY, v TEXT NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS m011_probes
            (probe_id TEXT PRIMARY KEY, op TEXT NOT NULL UNIQUE,
             challenge TEXT NOT NULL UNIQUE, request_sha256 TEXT NOT NULL,
             remote_operation_sha256 TEXT NOT NULL,
             m009_head_receipt_sha256 TEXT NOT NULL,
             trust_generation INTEGER NOT NULL, state TEXT NOT NULL,
             receipt_sha256 TEXT UNIQUE,
             FOREIGN KEY(op) REFERENCES operations(op))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS m011_trust_gen
                         (authority_id TEXT PRIMARY KEY, generation INTEGER NOT NULL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS m011_keys
            (authority_id TEXT NOT NULL, key_id TEXT NOT NULL,
             public_key_sha256 TEXT NOT NULL, PRIMARY KEY(authority_id,key_id))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS m011_revoked
                         (authority_id TEXT NOT NULL, key_id TEXT NOT NULL,
                          PRIMARY KEY(authority_id,key_id))""")
        self.db.execute("INSERT OR IGNORE INTO m011_meta VALUES (?,?)", ("schema",STORE_SCHEMA))
        if self.db.execute("SELECT v FROM m011_meta WHERE k='schema'").fetchone() != (STORE_SCHEMA,):
            self.close()
            raise SignedRecoveryHold("M011 local database schema mismatch")

    def close(self):
        self.ledger.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _begin(self):
        self.db.execute("BEGIN IMMEDIATE")

    def _rollback_if_open(self):
        if self.db.in_transaction:
            self.db.execute("ROLLBACK")

    def plan_probe(self, *, op, probe_id, challenge, request_sha256,
                   expected_remote_operation_sha256,
                   expected_m009_head_receipt_sha256,
                   trust_generation, failpoint=None):
        """Persist one opaque inquiry before an external call; never sends it."""
        if failpoint is not None and failpoint not in PROBE_FAILURE_POINTS:
            raise SignedRecoveryHold("invalid test-only probe failure point")
        _name(op, "operation")
        _name(probe_id, "probe id")
        if type(challenge) is not str or CHALLENGE.fullmatch(challenge) is None:
            raise SignedRecoveryHold("invalid recovery challenge")
        _sha(request_sha256, "query digest")
        _sha(expected_remote_operation_sha256, "remote operation binding")
        _sha(expected_m009_head_receipt_sha256, "M009 receipt binding")
        _counter(trust_generation, "planned trust generation", 1)
        self._begin()
        try:
            entry = self.db.execute("SELECT state FROM operations WHERE op=?", (op,)).fetchone()
            if entry is None or entry[0] not in ("PREPARED", "UNKNOWN"):
                raise SignedRecoveryHold("only existing unresolved operation may be queried")
            if self.db.execute("SELECT 1 FROM m011_probes WHERE op=?", (op,)).fetchone():
                raise SignedRecoveryHold("single outstanding recovery inquiry per operation")
            try:
                self.db.execute(
                    "INSERT INTO m011_probes VALUES (?,?,?,?,?,?,?,'PENDING',NULL)",
                    (probe_id, op, challenge, request_sha256,
                     expected_remote_operation_sha256,
                     expected_m009_head_receipt_sha256, trust_generation)
                )
            except sqlite3.IntegrityError as exc:
                raise SignedRecoveryHold("probe/challenge replay") from exc
            # A planned outbound query means we must fail closed on response loss.
            self.db.execute("UPDATE operations SET state='UNKNOWN' WHERE op=?", (op,))
            _failure(failpoint, "BEFORE_PROBE_COMMIT")
            self.db.execute("COMMIT")
        except BaseException:
            self._rollback_if_open()
            raise
        _failure(failpoint, "AFTER_PROBE_COMMIT")
        return self.status()

    def mark_partition(self, *, op):
        """A transport outage is never COMMITTED or REJECTED evidence."""
        _name(op, "operation")
        self._begin()
        try:
            entry = self.db.execute("SELECT state FROM operations WHERE op=?", (op,)).fetchone()
            probe = self.db.execute("SELECT state FROM m011_probes WHERE op=?", (op,)).fetchone()
            if entry is None or entry[0] not in ("PREPARED", "UNKNOWN") or probe != ("PENDING",):
                raise SignedRecoveryHold("only unresolved planned inquiry can be partitioned")
            self.db.execute("UPDATE operations SET state='UNKNOWN' WHERE op=?", (op,))
            self.db.execute("COMMIT")
        except BaseException:
            self._rollback_if_open()
            raise
        return self.status()

    def _trust_transition(self, pinned):
        """Persist a monotonic *local* trust/revocation review view atomically."""
        authority = pinned.authority_id
        row = self.db.execute(
            "SELECT generation FROM m011_trust_gen WHERE authority_id=?", (authority,)
        ).fetchone()
        if row is not None and pinned.generation < row[0]:
            raise SignedRecoveryHold("rollback of locally observed trust generation")
        old = {
            record[0]: record[1]
            for record in self.db.execute(
                "SELECT key_id, public_key_sha256 FROM m011_keys WHERE authority_id=?",
                (authority,)
            )
        }
        previous_revoked = {
            rec[0] for rec in self.db.execute(
                "SELECT key_id FROM m011_revoked WHERE authority_id=?", (authority,)
            )
        }
        if not previous_revoked.issubset(pinned.revoked_key_ids):
            raise SignedRecoveryHold("attempt to clear local key revocation tombstone")
        for key_id, key in pinned.public_keys.items():
            key_sha = sha256(key).hexdigest()
            if key_id in old and old[key_id] != key_sha:
                raise SignedRecoveryHold("signer key ID rebound to different material")
        for key_id, key in pinned.public_keys.items():
            self.db.execute(
                "INSERT OR IGNORE INTO m011_keys VALUES (?,?,?)",
                (authority, key_id, sha256(key).hexdigest())
            )
        for key_id in pinned.revoked_key_ids:
            self.db.execute(
                "INSERT OR IGNORE INTO m011_revoked VALUES (?,?)", (authority,key_id)
            )
        self.db.execute(
            "INSERT INTO m011_trust_gen VALUES (?,?) ON CONFLICT(authority_id)"
            " DO UPDATE SET generation=excluded.generation",
            (authority, pinned.generation)
        )

    def apply_signed_result(self, *, receipt, trust, expected_authority, now,
                            failpoint=None):
        """Atomic LOCAL signed-result capture; not independent remote authority."""
        if failpoint is not None and failpoint not in RECEIPT_FAILURE_POINTS:
            raise SignedRecoveryHold("invalid test-only signed result failure point")
        verified = verify_signed_recovery_receipt(
            receipt=receipt, trust=trust, expected_authority=expected_authority, now=now
        )
        row = verified["verified_receipt_copy"]
        pinned = verified["pinned_trust_copy"]
        signed_digest = verified["receipt_sha256"]
        self._begin()
        try:
            probe = self.db.execute(
                "SELECT op, challenge, request_sha256, remote_operation_sha256, "
                "m009_head_receipt_sha256, trust_generation, state "
                "FROM m011_probes WHERE probe_id=?", (row["probe_id"],)
            ).fetchone()
            if probe is None or probe[6] != "PENDING":
                raise SignedRecoveryHold("no pending inquiry or signed receipt replay")
            op, challenge, request_digest, remote_op, m009_hash, trust_at_plan, _ = probe
            if (op != row["operation_id"] or challenge != row["challenge"] or
                request_digest != row["request_sha256"] or
                remote_op != row["remote_operation_sha256"] or
                m009_hash != row["m009_head_receipt_sha256"] or
                row["trust_generation"] < trust_at_plan):
                raise SignedRecoveryHold("signed reply not bound to durable inquiry")
            operation = self.db.execute(
                "SELECT scope,prior_digest,candidate_digest,sequence,epoch,fence,state "
                "FROM operations WHERE op=?", (op,)
            ).fetchone()
            if operation is None or operation[6] != "UNKNOWN":
                raise SignedRecoveryHold("operation missing, finalized or not UNKNOWN")
            scope, prior, candidate, seq, epoch, fence, _ = operation
            if (scope != row["scope"] or prior != row["prior_head_sha256"] or
                candidate != row["candidate_head_sha256"] or
                seq != row["sequence"] or epoch != row["owner_epoch"] or
                fence != row["fence_generation"]):
                raise SignedRecoveryHold("signed reply not bound to M010 candidate")
            head = self.db.execute(
                "SELECT sequence,epoch,fence,digest FROM head WHERE scope=?", (scope,)
            ).fetchone()
            if (head is None or head[3] != prior or head[0]+1 != seq or
                epoch < head[1] or epoch > head[1]+1 or fence <= head[2]):
                raise SignedRecoveryHold("local head changed; remote reply not applicable")
            self._trust_transition(pinned)
            if row["result"] == "COMMITTED":
                self.db.execute(
                    "UPDATE head SET sequence=?,epoch=?,fence=?,digest=? WHERE scope=?",
                    (seq,epoch,fence,candidate,scope)
                )
                local_op_state = "COMMIT_RECORDED_REVIEW_ONLY"
                local_probe_state = "SIGNED_COMMIT_RECORDED_REVIEW_ONLY"
            else:
                local_op_state = "REJECTED"
                local_probe_state = "SIGNED_REJECTION_RECORDED_REVIEW_ONLY"
            self.db.execute(
                "UPDATE operations SET state=?,receipt_digest=? WHERE op=?",
                (local_op_state,signed_digest,op)
            )
            self.db.execute(
                "UPDATE m011_probes SET state=?,receipt_sha256=? WHERE probe_id=?",
                (local_probe_state,signed_digest,row["probe_id"])
            )
            _failure(failpoint, "BEFORE_SIGNED_RESULT_COMMIT")
            self.db.execute("COMMIT")
        except BaseException:
            self._rollback_if_open()
            raise
        _failure(failpoint, "AFTER_SIGNED_RESULT_COMMIT")
        return self.status()

    def status(self):
        """Return only source-safe local diagnostic tuples, never owner authority."""
        heads = self.db.execute(
            "SELECT scope,sequence,epoch,fence,digest FROM head ORDER BY scope"
        ).fetchall()
        operations = self.db.execute(
            "SELECT op,state,receipt_digest FROM operations ORDER BY op"
        ).fetchall()
        probes = self.db.execute(
            "SELECT probe_id,op,state,receipt_sha256 FROM m011_probes ORDER BY probe_id"
        ).fetchall()
        return {
            "schema": STORE_SCHEMA,
            "status": "LOCAL_SIGNED_RECOVERY_REVIEW_ONLY_HOLD",
            "heads": heads,
            "operations": operations,
            "probes": probes,
            "signed_claims_are_not_remote_current_state": True,
            "external_current_head_verified": False,
            "remote_commit_signature_is_authoritative_for_native_jobs": False,
            "remote_challenge_single_use_verified": False,
            "local_rollback_resistance_proven": False,
            "native_worker_dispatch_authorized": False,
            "worker_execution_authorized": False,
        }
