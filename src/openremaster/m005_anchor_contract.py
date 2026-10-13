"""M005: detached Ed25519 witness evidence verification (offline, non-authorizing).

No network client, state store, signing key, dispatch or production approval.
The supplied high-water checkpoint and freshness challenge MUST originate from an
independently authenticated, non-rollbackable source. This module cannot prove
that those inputs are current, nor that a local CAS receipt is genuine.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ANCHOR_SCHEMA = "ORCH-M005.SignedAnchor.v0"
CHECKPOINT_SCHEMA = "ORCH-M005.PinnedHighWater.v0"
OWNER_SCHEMA = "ORCH-M002.Structural.v0.OwnerSnapshot"
SIGNED_CONTEXT = b"OpenRemaster-ORCH-M005-anchor-v0\x00"
ANCHOR_FIELDS = frozenset({
    "schema", "authority_id", "key_id", "namespace", "challenge",
    "previous_anchor_sha256", "sequence", "store_revision", "owner_epoch",
    "source_revision", "corpus_sha256", "job_id", "attempt_id", "owner_id",
    "worker_id", "request_sha256", "owner_snapshot_sha256",
    "owner_receipt_sha256", "issued_utc", "expires_utc", "phase", "signature_b64",
})
CHECKPOINT_FIELDS = frozenset({
    "schema", "authority_id", "namespace", "sequence", "store_revision",
    "owner_epoch", "last_anchor_sha256",
})
OWNER_FIELDS = frozenset({
    "schema", "store_revision", "owner_epoch", "status", "job_id",
    "owner_id", "attempt_id", "expires_utc",
})
RECEIPT_FIELDS = frozenset({
    "status", "store_revision", "owner_epoch", "requires_external_witness_update",
    "dispatch_authorized", "request_digest",
})
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
CHALLENGE = re.compile(r"[A-Za-z0-9_-]{22,128}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
MAX_COUNTER = (1 << 63) - 1


class AnchorRejected(ValueError):
    """Fail-closed: input is not sufficient for structurally signed evidence."""


def _fields(obj, keys, label):
    if type(obj) is not dict or set(obj) != keys:
        raise AnchorRejected(f"{label}: missing or unexpected fields")


def _identifier(value, label):
    if type(value) is not str or not ID.fullmatch(value):
        raise AnchorRejected(f"{label}: invalid identifier")


def _digest(value, pattern, label):
    if type(value) is not str or not pattern.fullmatch(value):
        raise AnchorRejected(f"{label}: invalid digest")


def _counter(value, label):
    if type(value) is not int or not 0 <= value < MAX_COUNTER:
        raise AnchorRejected(f"{label}: invalid counter")


def _time(value, label):
    if type(value) is not str or not STAMP.fullmatch(value):
        raise AnchorRejected(f"{label}: require exact UTC seconds with Z")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AnchorRejected(f"{label}: invalid date") from exc
    return parsed


def _now(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise AnchorRejected("now: timezone-aware caller-supplied UTC clock required")
    return now.astimezone(timezone.utc)


def canonical_json(obj):
    """Documented Python JSON encoding. This is not RFC 8785/JCS."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AnchorRejected("invalid canonical JSON") from exc


def sha256_json(obj):
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def signing_message(anchor):
    """Signature covers the entire strict anchor payload, domain-separated."""
    _fields(anchor, ANCHOR_FIELDS, "anchor")
    unsigned = {k: v for k, v in anchor.items() if k != "signature_b64"}
    return SIGNED_CONTEXT + canonical_json(unsigned)


def _signed_anchor(anchor, trust_keys):
    _fields(anchor, ANCHOR_FIELDS, "anchor")
    if anchor["schema"] != ANCHOR_SCHEMA or anchor["phase"] != "COMMITTED":
        raise AnchorRejected("unsupported anchor version/phase")
    _identifier(anchor["authority_id"], "authority_id")
    _identifier(anchor["key_id"], "key_id")
    _identifier(anchor["namespace"], "namespace")
    if type(anchor["challenge"]) is not str or not CHALLENGE.fullmatch(anchor["challenge"]):
        raise AnchorRejected("invalid challenge")
    for name in ("job_id", "attempt_id", "owner_id", "worker_id"):
        _identifier(anchor[name], name)
    for name in ("previous_anchor_sha256", "corpus_sha256", "request_sha256", "owner_snapshot_sha256", "owner_receipt_sha256"):
        _digest(anchor[name], SHA64, name)
    _digest(anchor["source_revision"], SHA40, "source_revision")
    for name in ("sequence", "store_revision", "owner_epoch"):
        _counter(anchor[name], name)
    if not isinstance(trust_keys, dict):
        raise AnchorRejected("trust_keys must be a pinned mapping")
    key = trust_keys.get((anchor["authority_id"], anchor["key_id"]))
    if type(key) is not bytes or len(key) != 32:
        raise AnchorRejected("pinned Ed25519 public key unavailable")
    signature = anchor["signature_b64"]
    if type(signature) is not str or len(signature) > 128:
        raise AnchorRejected("malformed Ed25519 signature")
    try:
        raw = base64.b64decode(signature, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise AnchorRejected("invalid signature encoding") from exc
    if len(raw) != 64 or base64.b64encode(raw).decode("ascii") != signature:
        raise AnchorRejected("noncanonical Ed25519 signature encoding")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(raw, signing_message(anchor))
    except (InvalidSignature, ValueError) as exc:
        raise AnchorRejected("invalid signature or signed payload") from exc


def _checkpoint(checkpoint):
    _fields(checkpoint, CHECKPOINT_FIELDS, "independently pinned checkpoint")
    if checkpoint["schema"] != CHECKPOINT_SCHEMA:
        raise AnchorRejected("unknown checkpoint version")
    for name in ("authority_id", "namespace"):
        _identifier(checkpoint[name], name)
    for name in ("sequence", "store_revision", "owner_epoch"):
        _counter(checkpoint[name], name)
    _digest(checkpoint["last_anchor_sha256"], SHA64, "last_anchor_sha256")
    if checkpoint["owner_epoch"] > checkpoint["store_revision"]:
        raise AnchorRejected("checkpoint epoch exceeds revision")


def _owner_snapshot(state):
    _fields(state, OWNER_FIELDS, "owner snapshot")
    if state["schema"] != OWNER_SCHEMA or state["status"] != "ACTIVE":
        raise AnchorRejected("M005 only models an ACTIVE owner acquisition")
    for name in ("job_id", "attempt_id", "owner_id"):
        _identifier(state[name], name)
    _time(state["expires_utc"], "owner expiry")
    _counter(state["owner_epoch"], "owner epoch")
    _counter(state["store_revision"], "owner revision")
    if state["owner_epoch"] < 1 or state["owner_epoch"] > state["store_revision"]:
        raise AnchorRejected("invalid ACTIVE owner counters")


def _owner_receipt(receipt):
    _fields(receipt, RECEIPT_FIELDS, "owner commit receipt")
    if (receipt["status"] != "CAS_COMMITTED_LAB_ONLY"
            or receipt["dispatch_authorized"] is not False
            or receipt["requires_external_witness_update"] is not True):
        raise AnchorRejected("not a committed M003 laboratory receipt")
    _counter(receipt["store_revision"], "receipt revision")
    _counter(receipt["owner_epoch"], "receipt epoch")
    _digest(receipt["request_digest"], SHA64, "request_digest")


def verify_detached_anchor(
    *, anchor, independent_checkpoint, owner_snapshot, owner_receipt,
    trusted_public_keys, expected_namespace, expected_authority,
    expected_worker, expected_challenge, expected_source_revision,
    expected_corpus_sha256, expected_request_sha256, now,
):
    """Verify a signed *candidate* against caller-pinned inputs.

    Returned next_checkpoint MUST NOT be treated as a durable/remote commit.
    This function cannot prove any checkpoint is the current external high-water
    mark, that a challenge is fresh, or that an M003 receipt is authentic.
    """
    if anchor is None or independent_checkpoint is None:
        raise AnchorRejected("partition/missing external attestation: BLOCKED")
    _checkpoint(independent_checkpoint)
    _owner_snapshot(owner_snapshot)
    _owner_receipt(owner_receipt)
    _signed_anchor(anchor, trusted_public_keys)
    for name, value in (
        ("expected_namespace", expected_namespace),
        ("expected_authority", expected_authority),
        ("expected_worker", expected_worker),
    ):
        _identifier(value, name)
    if type(expected_challenge) is not str or not CHALLENGE.fullmatch(expected_challenge):
        raise AnchorRejected("invalid caller challenge")
    _digest(expected_source_revision, SHA40, "expected source commit")
    _digest(expected_corpus_sha256, SHA64, "expected corpus SHA")
    _digest(expected_request_sha256, SHA64, "expected request SHA")
    moment = _now(now)
    if _time(owner_snapshot["expires_utc"], "owner expiry") <= moment:
        raise AnchorRejected("owner lease expired")
    issued = _time(anchor["issued_utc"], "issued_utc")
    expires = _time(anchor["expires_utc"], "expires_utc")
    if not issued <= moment < expires or not timedelta(0) < expires - issued <= timedelta(seconds=60):
        raise AnchorRejected("anchor expired, future, or exceeds 60-second signed window")
    for field, expected in (
        ("namespace", expected_namespace),
        ("authority_id", expected_authority),
        ("worker_id", expected_worker),
        ("challenge", expected_challenge),
        ("source_revision", expected_source_revision),
        ("corpus_sha256", expected_corpus_sha256),
        ("request_sha256", expected_request_sha256),
    ):
        if anchor[field] != expected:
            raise AnchorRejected(f"anchor mismatch: {field}")
    if (independent_checkpoint["namespace"] != expected_namespace
            or independent_checkpoint["authority_id"] != expected_authority):
        raise AnchorRejected("independent checkpoint scope mismatch")
    for name in ("job_id", "attempt_id", "owner_id"):
        if anchor[name] != owner_snapshot[name]:
            raise AnchorRejected(f"owner identity mismatch: {name}")
    if anchor["sequence"] != independent_checkpoint["sequence"] + 1:
        raise AnchorRejected("nonmonotonic signed sequence")
    if anchor["previous_anchor_sha256"] != independent_checkpoint["last_anchor_sha256"]:
        raise AnchorRejected("signed hash chain fork or stale checkpoint")
    if anchor["store_revision"] != independent_checkpoint["store_revision"] + 1:
        raise AnchorRejected("owner revision gap or rollback")
    if not independent_checkpoint["owner_epoch"] <= anchor["owner_epoch"] <= independent_checkpoint["owner_epoch"] + 1:
        raise AnchorRejected("owner epoch rollback or invalid jump")
    if (anchor["store_revision"] != owner_snapshot["store_revision"]
            or anchor["owner_epoch"] != owner_snapshot["owner_epoch"]
            or anchor["store_revision"] != owner_receipt["store_revision"]
            or anchor["owner_epoch"] != owner_receipt["owner_epoch"]):
        raise AnchorRejected("owner receipt/state counter mismatch")
    if owner_receipt["request_digest"] != expected_request_sha256:
        raise AnchorRejected("M003 request digest mismatch")
    if anchor["owner_snapshot_sha256"] != sha256_json(owner_snapshot):
        raise AnchorRejected("owner state content mismatch")
    if anchor["owner_receipt_sha256"] != sha256_json(owner_receipt):
        raise AnchorRejected("owner receipt content mismatch")
    next_checkpoint = {
        "schema": CHECKPOINT_SCHEMA,
        "authority_id": anchor["authority_id"],
        "namespace": anchor["namespace"],
        "sequence": anchor["sequence"],
        "store_revision": anchor["store_revision"],
        "owner_epoch": anchor["owner_epoch"],
        "last_anchor_sha256": sha256_json(anchor),
    }
    return {
        "status": "SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF",
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
        "current_external_high_water_verified": False,
        "independent_owner_cas_authenticity_verified": False,
        "next_checkpoint_proposal_only": next_checkpoint,
    }


def classify_partition(observation):
    """An availability hint is *never* an authorization to execute."""
    if observation not in ("ONLINE", "TIMEOUT", "PARTITIONED", "UNKNOWN", "STALE"):
        raise AnchorRejected("unknown witness observation")
    return {
        "status": "SIGNED_RECEIPT_STILL_REQUIRED" if observation == "ONLINE" else "BLOCKED_NO_FRESH_WITNESS",
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
    }
