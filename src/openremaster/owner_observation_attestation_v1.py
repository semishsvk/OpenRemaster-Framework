"""M008 OwnerObservationAttestation.v1: dual-signer structural evidence review ONLY.

Two separately pinned Ed25519 public keys verify signatures over an owner
observation and an independent-head *claim*.  Caller-supplied head, time,
challenge and public keys CANNOT establish current external owner authority.
No network, signing secrets, SQLite mutations, worker or game runtime access.
Every output explicitly forbids dispatch and treats any success as a candidate.
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

from openremaster.source_freshness_guard_v1 import PINNED_R14_PILOT_SHA256

OWNER_SCHEMA = "ORF-M008.OwnerObservationSigned.v1"
HEAD_SCHEMA = "ORF-M008.ExternalMonotonicHeadSigned.v1"
PIN_SCHEMA = "ORF-M008.PinnedHead.v1"
EXPECT_SCHEMA = "ORF-M008.ReviewExpectations.v1"
OWNER_SIGN_CONTEXT = b"OpenRemaster-M008-OwnerObservation-v1\x00"
HEAD_SIGN_CONTEXT = b"OpenRemaster-M008-IndependentHead-v1\x00"
MAX_COUNTER = (1 << 63) - 1
HASH = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}\Z")
CHALLENGE = re.compile(r"[A-Za-z0-9_-]{22,128}\Z")
UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
OWNER_FIELDS = frozenset((
    "schema", "authority_id", "key_id", "namespace", "job_id",
    "attempt_id", "owner_id", "worker_id", "owner_epoch_label",
    "fence_generation", "owner_work_scope_sha256", "source_sha256",
    "source_git_revision", "corpus_sha256", "request_sha256",
    "observation_sha256", "r14_frozen_pilot_sha256", "challenge",
    "issued_utc", "expires_utc", "signature_b64",
))
HEAD_FIELDS = frozenset((
    "schema", "authority_id", "key_id", "namespace", "sequence",
    "previous_head_sha256", "owner_attestation_sha256", "job_id",
    "owner_epoch_label", "fence_generation", "owner_work_scope_sha256",
    "observation_sha256", "source_git_revision", "corpus_sha256",
    "request_sha256", "challenge", "issued_utc", "expires_utc",
    "signature_b64",
))
PIN_FIELDS = frozenset((
    "schema", "authority_id", "namespace", "sequence",
    "fence_generation", "last_head_sha256",
))
EXPECT_FIELDS = frozenset((
    "schema", "namespace", "job_id", "attempt_id", "owner_id",
    "worker_id", "owner_authority_id", "head_authority_id",
    "owner_work_scope_sha256", "source_sha256", "source_git_revision",
    "corpus_sha256", "request_sha256", "observation_sha256",
    "challenge",
))


class ObservationRejected(ValueError):
    """The supplied record or trust assumption fails closed."""


def _exact(obj, keys, label):
    if type(obj) is not dict or set(obj) != keys:
        raise ObservationRejected(f"{label}: missing or extra fields")
    return obj


def _id(value, label):
    if type(value) is not str or not ID.fullmatch(value):
        raise ObservationRejected(f"{label}: invalid identifier")
    return value


def _hash(value, label):
    if type(value) is not str or not HASH.fullmatch(value):
        raise ObservationRejected(f"{label}: invalid SHA256")
    return value


def _git(value):
    if type(value) is not str or not GIT_SHA.fullmatch(value):
        raise ObservationRejected("Git revision: invalid 40-hex")
    return value


def _counter(value, label, minimum=0):
    if type(value) is not int or not minimum <= value < MAX_COUNTER:
        raise ObservationRejected(f"{label}: invalid bounded integer")
    return value


def _challenge(value):
    if type(value) is not str or not CHALLENGE.fullmatch(value):
        raise ObservationRejected("challenge: invalid")
    return value


def _date(value, label):
    if type(value) is not str or not UTC.fullmatch(value):
        raise ObservationRejected(f"{label}: UTC Z seconds required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError as exc:
        raise ObservationRejected(f"{label}: invalid timestamp") from exc


def _now(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ObservationRejected("now: timezone-aware external clock required")
    return value.astimezone(timezone.utc)


def canonical_json(obj):
    """Python-only exact canonical encoding, not RFC 8785/JCS."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise ObservationRejected("not canonicalizable JSON") from exc


def sha256_json(obj):
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def owner_signing_message(record):
    _exact(record, OWNER_FIELDS, "owner")
    return OWNER_SIGN_CONTEXT + canonical_json(
        {k: v for k, v in record.items() if k != "signature_b64"}
    )


def head_signing_message(record):
    _exact(record, HEAD_FIELDS, "head")
    return HEAD_SIGN_CONTEXT + canonical_json(
        {k: v for k, v in record.items() if k != "signature_b64"}
    )


def _verify_sig(record, key, message, label):
    if type(key) is not bytes or len(key) != 32:
        raise ObservationRejected(f"{label}: unavailable pinned Ed25519 key")
    sig = record["signature_b64"]
    if type(sig) is not str or len(sig) > 128:
        raise ObservationRejected(f"{label}: invalid signature field")
    try:
        raw = base64.b64decode(sig, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ObservationRejected(f"{label}: malformed signature encoding") from exc
    if len(raw) != 64 or base64.b64encode(raw).decode("ascii") != sig:
        raise ObservationRejected(f"{label}: noncanonical signature")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(raw, message)
    except (ValueError, InvalidSignature) as exc:
        raise ObservationRejected(f"{label}: signature rejected") from exc


def _window(doc, now, label):
    start = _date(doc["issued_utc"], label + ".issued_utc")
    end = _date(doc["expires_utc"], label + ".expires_utc")
    if not start <= now < end or not timedelta(0) < end-start <= timedelta(seconds=60):
        raise ObservationRejected(f"{label}: expired, future or >60 seconds")
    return start, end


def _review_source_snapshot(review, observation_sha256):
    # The result is caller-supplied. Even if all fields match, its origin,
    # capture clock and independent owner identity remain UNAUTHENTICATED.
    if type(review) is not dict:
        raise ObservationRejected("R14 sealed source review unavailable")
    required = {
        "status": "SOURCE_FRESHNESS_REVIEW_ONLY_HOLD",
        "source_pilot_sha256_pinned": PINNED_R14_PILOT_SHA256,
        "sealed_pilot_bytes_verified": True,
        "immutable_matched_count": 61,
        "immutable_source_drift_paths": [],
        "live_observation_stable_within_read_pair": True,
        "current_owner_authority_verified": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
        "legacy_r14_full_acceptance_reclassified_as_pass": False,
    }
    for k,v in required.items():
        if k not in review or type(review[k]) is not type(v) or review[k] != v:
            raise ObservationRejected("R14 source review missing/contradictory: " + k)
    if review.get("classification") not in (
        "LIVE_OWNER_OBSERVATION_CHANGED_UNATTESTED_HOLD",
        "LIVE_OWNER_OBSERVATION_STILL_UNATTESTED_HOLD",
    ):
        raise ObservationRejected("R14 observation classification untrusted")
    if review.get("live_observation_captured_sha256") != observation_sha256:
        raise ObservationRejected("R14 observation digest not bound")
    return True


def _pinned_head(record):
    _exact(record, PIN_FIELDS, "pinned head")
    if record["schema"] != PIN_SCHEMA:
        raise ObservationRejected("unsupported pinned-head schema")
    _id(record["authority_id"], "pinned authority")
    _id(record["namespace"], "pinned namespace")
    _counter(record["sequence"], "pinned sequence")
    _counter(record["fence_generation"], "pinned generation")
    _hash(record["last_head_sha256"], "pinned head hash")


def verify_dual_attestation(
    *, owner, head, pinned_head, independent_expectations,
    source_freshness_review, pinned_public_keys, now,
):
    """Check both signatures and cross-binding; *never* assert current authority.

    The signing keys, clock, expectations, challenge and pinned-head all arrive
    from the caller. There is no external current-head query, nonce-spend or
    native CAS receipt. A replayed internally consistent bundle can pass this
    candidate review even when it is historically stale.
    """
    moment = _now(now)
    _exact(owner, OWNER_FIELDS, "owner")
    _exact(head, HEAD_FIELDS, "external head")
    _exact(independent_expectations, EXPECT_FIELDS, "expectations")
    _pinned_head(pinned_head)
    if owner["schema"] != OWNER_SCHEMA or head["schema"] != HEAD_SCHEMA:
        raise ObservationRejected("unsupported signed contract versions")
    if independent_expectations["schema"] != EXPECT_SCHEMA:
        raise ObservationRejected("unexpected expectation schema")
    for field in ("authority_id", "key_id", "namespace", "job_id",
                  "attempt_id", "owner_id", "worker_id", "owner_epoch_label"):
        _id(owner[field], "owner." + field)
    for field in ("authority_id", "key_id", "namespace", "job_id",
                  "owner_epoch_label"):
        _id(head[field], "head." + field)
    for field in ("owner_work_scope_sha256", "source_sha256", "corpus_sha256",
                  "request_sha256", "observation_sha256", "r14_frozen_pilot_sha256"):
        _hash(owner[field], "owner." + field)
    for field in ("owner_work_scope_sha256", "observation_sha256",
                  "corpus_sha256", "request_sha256", "previous_head_sha256",
                  "owner_attestation_sha256"):
        _hash(head[field], "head." + field)
    _git(owner["source_git_revision"])
    _git(head["source_git_revision"])
    _challenge(owner["challenge"])
    _challenge(head["challenge"])
    _counter(owner["fence_generation"], "owner fence", 1)
    _counter(head["fence_generation"], "external-head fence", 1)
    _counter(head["sequence"], "external-head sequence", 1)

    for field in ("namespace", "job_id", "attempt_id", "owner_id", "worker_id",
                  "owner_work_scope_sha256", "source_sha256",
                  "source_git_revision", "corpus_sha256",
                  "request_sha256", "observation_sha256", "challenge"):
        actual = independent_expectations[field]
        if actual != owner[field] or type(actual) is not type(owner[field]):
            raise ObservationRejected("owner expectation mismatch: " + field)
    if independent_expectations["owner_authority_id"] != owner["authority_id"]:
        raise ObservationRejected("owner signer trust-scope mismatch")
    if independent_expectations["head_authority_id"] != head["authority_id"]:
        raise ObservationRejected("head signer trust-scope mismatch")
    if owner["r14_frozen_pilot_sha256"] != PINNED_R14_PILOT_SHA256:
        raise ObservationRejected("frozen R14 pilot identity not pinned")

    owner_start, owner_end = _window(owner, moment, "owner")
    head_start, head_end = _window(head, moment, "head")
    if head_start < owner_start or head_end > owner_end:
        raise ObservationRejected("external head timing outside owner interval")

    if (owner["authority_id"] == head["authority_id"] or
            owner["namespace"] != head["namespace"] or
            pinned_head["authority_id"] != head["authority_id"] or
            pinned_head["namespace"] != head["namespace"]):
        raise ObservationRejected("owner/head signer role or namespace confusion")
    if type(pinned_public_keys) is not dict:
        raise ObservationRejected("trusted public key registry not supplied")
    key_owner = pinned_public_keys.get(("owner", owner["authority_id"], owner["key_id"]))
    key_head = pinned_public_keys.get(("head", head["authority_id"], head["key_id"]))
    if type(key_owner) is not bytes or type(key_head) is not bytes or key_owner == key_head:
        raise ObservationRejected("pinned role-separated signer keys unavailable")
    _verify_sig(owner, key_owner, owner_signing_message(owner), "owner")
    _verify_sig(head, key_head, head_signing_message(head), "head")

    if head["sequence"] != pinned_head["sequence"] + 1:
        raise ObservationRejected("sequence replay/gap")
    if head["previous_head_sha256"] != pinned_head["last_head_sha256"]:
        raise ObservationRejected("external head fork/stale anchor")
    if head["fence_generation"] != pinned_head["fence_generation"] + 1:
        raise ObservationRejected("new-owner fencing generation not monotonic +1")
    if head["fence_generation"] != owner["fence_generation"]:
        raise ObservationRejected("owner/head fencing generations disagree")
    for field in ("namespace", "job_id", "owner_epoch_label",
                  "owner_work_scope_sha256", "observation_sha256",
                  "source_git_revision", "corpus_sha256",
                  "request_sha256", "challenge"):
        if head[field] != owner[field]:
            raise ObservationRejected("signed cross-binding mismatch: " + field)
    if head["owner_attestation_sha256"] != sha256_json(owner):
        raise ObservationRejected("head does not bind entire signed owner attestation")
    _review_source_snapshot(source_freshness_review, owner["observation_sha256"])

    next_head_proposal = {
        "schema": PIN_SCHEMA,
        "authority_id": head["authority_id"],
        "namespace": head["namespace"],
        "sequence": head["sequence"],
        "fence_generation": head["fence_generation"],
        "last_head_sha256": sha256_json(head),
    }
    return {
        "status": "TWO_SIGNATURES_STRUCTURALLY_VALID_NOT_CURRENT_AUTHORITY",
        "signed_owner_candidate_sha256": sha256_json(owner),
        "signed_head_candidate_sha256": sha256_json(head),
        "next_head_proposal_only": next_head_proposal,
        "r14_historical_pilot_sha256": PINNED_R14_PILOT_SHA256,
        "observation_content_verified_against_live_owner": False,
        "source_review_origin_authenticated": False,
        "signer_roles_cryptographically_distinct": True,
        "current_external_highwater_verified": False,
        "owner_epoch_cross_domain_mapped": False,
        "owner_work_scope_resolver_authenticated": False,
        "external_challenge_uniqueness_verified": False,
        "durable_nonce_spend_verified": False,
        "owner_cas_receipt_verified": False,
        "worker_side_fence_verified": False,
        "production_owner_authorized": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
    }


def classify_external_availability(value):
    """Network status is descriptive only, never owner authority."""
    if value not in ("ONLINE", "TIMEOUT", "PARTITIONED", "UNKNOWN", "STALE"):
        raise ObservationRejected("invalid witness availability")
    return {
        "status": "REMOTE_PROOF_NOT_CONFIRMED" if value == "ONLINE"
                  else "EXTERNAL_CURRENTNESS_UNAVAILABLE_HOLD",
        "current_external_highwater_verified": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
    }
