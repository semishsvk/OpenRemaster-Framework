"""M008: offline signed owner-observation review, not execution authority.

Ed25519 confirms which bytes an attestor signed. M005 verification confirms a
separate candidate signature. No locally supplied high-water, claimed R14 HMAC
review, clock or nonce can prove current externally trusted ownership.
Never reads real owner-state files, runs workers, signs production data, or
upgrades review evidence into native dispatch.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from openremaster.m005_anchor_contract import (
    AnchorRejected, canonical_json, sha256_json, verify_detached_anchor,
)
from openremaster.source_freshness_guard_v1 import (
    CAPTURE_SCHEMA, LIVE_OWNER_OBSERVATION,
)

ATTEST_SCHEMA = "ORF-M008.OwnerObservationAttestation.v1"
HIGHWATER_SCHEMA = "ORF-M008.PinnedOwnerObservationHighwater.v1"
AUDIENCE = "ORF-ExternalOwnerObservation-ReviewOnly-v1"
SIGN_CONTEXT = b"OpenRemaster|OwnerObservationAttestation|v1\x00"
R14_POLICY_SCHEMA = "OpenRemaster.R13SignedOwnerModeDecision.v1"
R14_ANCHOR_SCHEMA = "OpenRemaster.R14IndependentRegistryAnchor.v1"
R14_ANCHOR_AUDIENCE = "ORF-ExternalRegistryAnchor-OwnerReviewOnly-v1"
R14_SOURCE_GUARD_SCHEMA = "ORF.SourceFreshnessGuard.v1"
PILOT_SHA = "9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865"
M005_SCHEMA = "ORCH-M005.SignedAnchor.v0"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
CHALLENGE = re.compile(r"[A-Za-z0-9_-]{22,128}\Z")
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
MAX_COUNTER = (1 << 63) - 1

HIGHWATER_FIELDS = frozenset({
    "schema", "authority_id", "registry_id", "sequence", "owner_epoch_counter",
    "last_attestation_sha256",
})
ATTEST_FIELDS = frozenset({
    "schema", "audience", "authority_id", "key_id", "registry_id",
    "project_id", "edition", "policy_epoch_id", "r14_owner_id", "m005_owner_id",
    "owner_work_scope_sha256", "r14_policy_sha256", "r14_anchor_sha256",
    "source_guard_sha256", "source_capture_sha256",
    "source_capture_finished_utc", "r14_source_sha256", "m005_source_revision",
    "corpus_sha256", "owner_observation_sha256", "owner_observation_size_bytes",
    "r14_owner_epoch_id", "owner_epoch_counter", "fence_generation",
    "nonce_sha256", "m005_anchor_sha256", "sequence",
    "previous_attestation_sha256", "challenge", "observed_utc", "issued_utc",
    "expires_utc", "signature_b64",
})
R14_POLICY_FIELDS = frozenset({
    "schema", "audience", "purpose", "mode", "project_id", "edition", "job_id",
    "work_identity_sha256", "owner_work_scope_sha256", "job_sha256",
    "legacy_envelope_sha256", "source_sha256", "checkpoint_sha256",
    "nonce_sha256", "owner_id", "owner_epoch", "lease_id", "policy_epoch",
    "fence_generation", "r5_operation_id", "legacy_permit_sha256",
    "r10_prestart_sha256", "r6_signed_ack_sha256", "issued_at_unix",
    "expires_at_unix", "mac",
})
R14_ANCHOR_FIELDS = frozenset({
    "schema", "audience", "registry_id", "external_anchor_sequence",
    "prior_external_anchor_sha256", "registry_event_count",
    "registry_mode_count", "last_registry_event_sha256",
    "source_registry_schema", "captured_at_unix", "expires_at_unix",
    "signer_id", "source_producer_id", "mac",
})


class ObservationRejected(ValueError):
    """Reject malformed, stale, forged, or semantically misbound evidence."""


def _fields(value, fields, label):
    if type(value) is not dict or set(value) != fields:
        raise ObservationRejected(f"{label}: missing/extra fields")
    return value


def _name(value, label):
    if type(value) is not str or NAME.fullmatch(value) is None:
        raise ObservationRejected(f"{label}: invalid identifier")
    return value


def _sha(value, pattern, label):
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ObservationRejected(f"{label}: invalid digest")
    return value


def _int(value, label, minimum=0):
    if type(value) is not int or not minimum <= value < MAX_COUNTER:
        raise ObservationRejected(f"{label}: invalid integer")
    return value


def _instant(value, label):
    if type(value) is not str or STAMP.fullmatch(value) is None:
        raise ObservationRejected(f"{label}: UTC seconds/Z required")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ObservationRejected(f"{label}: invalid timestamp") from exc


def _now(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ObservationRejected("now: timezone-aware clock required")
    return now.astimezone(timezone.utc)


def signing_message(attestation):
    _fields(attestation, ATTEST_FIELDS, "attestation")
    unsigned = {k: v for k, v in attestation.items() if k != "signature_b64"}
    try:
        return SIGN_CONTEXT + canonical_json(unsigned)
    except AnchorRejected as exc:
        raise ObservationRejected("invalid signed JSON") from exc


def _verify_signature(attestation, public_keys):
    if type(public_keys) is not dict:
        raise ObservationRejected("pinned public keys mapping required")
    key = public_keys.get((attestation["authority_id"], attestation["key_id"]))
    if type(key) is not bytes or len(key) != 32:
        raise ObservationRejected("pinned attestor Ed25519 key unavailable")
    value = attestation["signature_b64"]
    if type(value) is not str or len(value) > 128:
        raise ObservationRejected("invalid signature encoding")
    try:
        binary = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ObservationRejected("invalid base64 signature") from exc
    if len(binary) != 64 or base64.b64encode(binary).decode("ascii") != value:
        raise ObservationRejected("noncanonical Ed25519 signature")
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(binary, signing_message(attestation))
    except (InvalidSignature, ValueError) as exc:
        raise ObservationRejected("invalid attestation signature") from exc


def _highwater(highwater):
    _fields(highwater, HIGHWATER_FIELDS, "pinned high-water")
    if highwater["schema"] != HIGHWATER_SCHEMA:
        raise ObservationRejected("unsupported high-water schema")
    _name(highwater["authority_id"], "high-water authority")
    _name(highwater["registry_id"], "high-water registry")
    _int(highwater["sequence"], "high-water sequence")
    _int(highwater["owner_epoch_counter"], "high-water epoch")
    _sha(highwater["last_attestation_sha256"], HEX64, "high-water head")


def _policy(policy):
    _fields(policy, R14_POLICY_FIELDS, "original R14 signed policy")
    if policy["schema"] != R14_POLICY_SCHEMA:
        raise ObservationRejected("wrong R14 policy schema")
    if policy["audience"] != "ORF-HostLocal-ExclusiveNativeMode-OwnerReview-v1":
        raise ObservationRejected("wrong R14 policy audience")
    if policy["purpose"] != "EXCLUSIVE_LEGACY_OR_V2_MODE_REVIEW_ONLY":
        raise ObservationRejected("wrong owner policy purpose")
    if policy["mode"] not in ("LEGACY_V1_ALLOWED", "V2_REQUIRED"):
        raise ObservationRejected("wrong R14 owner mode")
    for f in ("project_id","edition","job_id","owner_id","owner_epoch",
              "lease_id","policy_epoch"):
        _name(policy[f], "R14 policy " + f)
    for f in ("owner_work_scope_sha256","source_sha256","nonce_sha256",
              "work_identity_sha256","job_sha256","legacy_envelope_sha256",
              "checkpoint_sha256","mac"):
        _sha(policy[f], HEX64, "R14 policy " + f)
    for f in ("r5_operation_id","legacy_permit_sha256",
              "r10_prestart_sha256","r6_signed_ack_sha256"):
        if policy[f] is not None:
            # R5 ID is a name; other optional fields are SHA-256 digests.
            if f == "r5_operation_id":
                _name(policy[f], f)
            else:
                _sha(policy[f], HEX64, f)
    for f in ("fence_generation","issued_at_unix","expires_at_unix"):
        _int(policy[f], "R14 policy " + f)
    if policy["fence_generation"] < 1 or policy["expires_at_unix"] <= policy["issued_at_unix"]:
        raise ObservationRejected("invalid R14 policy fence/window")


def _anchor14(anchor):
    _fields(anchor, R14_ANCHOR_FIELDS, "R14 anchor")
    if anchor["schema"] != R14_ANCHOR_SCHEMA or anchor["audience"] != R14_ANCHOR_AUDIENCE:
        raise ObservationRejected("R14 anchor wrong signing domain")
    if anchor["source_registry_schema"] != "OpenRemaster.R13HostLocalExclusiveOwnerRegistry.v1":
        raise ObservationRejected("R14 anchor registry version mismatch")
    for f in ("registry_id","signer_id","source_producer_id"):
        _name(anchor[f], "R14 anchor " + f)
    if anchor["signer_id"] == anchor["source_producer_id"]:
        raise ObservationRejected("R14 anchor self-signed")
    for f in ("prior_external_anchor_sha256","last_registry_event_sha256","mac"):
        _sha(anchor[f], HEX64, "R14 anchor " + f)
    for f in ("external_anchor_sequence","registry_event_count",
              "registry_mode_count","captured_at_unix","expires_at_unix"):
        _int(anchor[f], "R14 anchor " + f)
    if anchor["external_anchor_sequence"] < 1:
        raise ObservationRejected("invalid R14 anchor sequence")


def _source_guard(review):
    if type(review) is not dict:
        raise ObservationRejected("source guard review required")
    if review.get("schema") != R14_SOURCE_GUARD_SCHEMA or (
        review.get("status") != "SOURCE_FRESHNESS_REVIEW_ONLY_HOLD"
    ):
        raise ObservationRejected("source guard hold absent")
    if review.get("classification") not in (
        "LIVE_OWNER_OBSERVATION_CHANGED_UNATTESTED_HOLD",
        "LIVE_OWNER_OBSERVATION_STILL_UNATTESTED_HOLD",
    ):
        raise ObservationRejected("source guard classification is not stable review")
    if (review.get("source_pilot_sha256_pinned") != PILOT_SHA
        or review.get("sealed_pilot_bytes_verified") is not True
        or type(review.get("immutable_matched_count")) is not int
        or review["immutable_matched_count"] != 61
        or type(review.get("historical_reference_count")) is not int
        or review["historical_reference_count"] != 62
        or review.get("claimed_capture_timestamp_recent") is not True
        or review.get("live_observation_path") != LIVE_OWNER_OBSERVATION
        or review.get("immutable_source_drift_paths") != []
        or review.get("live_observation_stable_within_read_pair") is not True):
        raise ObservationRejected("source guard not complete and stable")
    for field in ("dispatch_authorized","worker_execution_authorized",
                  "current_owner_authority_verified",
                  "legacy_r14_full_acceptance_reclassified_as_pass"):
        if review.get(field) is not False:
            raise ObservationRejected("source guard asserted authorization")
    _sha(review.get("live_observation_captured_sha256"), HEX64, "source observation")
    _int(review.get("live_observation_byte_count"), "observation size")


def _capture(capture, source_guard):
    """Bind the exact M007 double-read hash capture, never owner payload bytes."""
    _fields(capture, frozenset(("schema", "started_utc", "finished_utc", "files")),
            "source capture")
    if capture["schema"] != CAPTURE_SCHEMA:
        raise ObservationRejected("unsupported source capture version")
    started = _instant(capture["started_utc"], "capture start")
    finished = _instant(capture["finished_utc"], "capture finish")
    if started > finished or finished - started > timedelta(seconds=60):
        raise ObservationRejected("invalid source capture interval")
    files = capture["files"]
    if type(files) is not dict or len(files) != 62 or LIVE_OWNER_OBSERVATION not in files:
        raise ObservationRejected("source capture must contain exactly 62 pinned paths")
    for name, item in files.items():
        if type(name) is not str or type(item) is not dict or set(item) != {
            "first_sha256", "second_sha256", "byte_count"
        }:
            raise ObservationRejected("invalid hash-only file capture")
        _sha(item["first_sha256"], HEX64, "first captured SHA")
        _sha(item["second_sha256"], HEX64, "second captured SHA")
        _int(item["byte_count"], "captured file size")
        if item["byte_count"] > 67108864:
            raise ObservationRejected("captured file size beyond bounded limit")
    owner = files[LIVE_OWNER_OBSERVATION]
    if (owner["first_sha256"] != owner["second_sha256"] or
        owner["second_sha256"] != source_guard["live_observation_captured_sha256"] or
        owner["byte_count"] != source_guard["live_observation_byte_count"]):
        raise ObservationRejected("owner double-read differs from signed source review")


def verify_attestation(*, attestation, independently_pinned_highwater,
                       source_guard_review, source_guard_capture,
                       r14_signed_policy, r14_review_anchor,
                       m005_verified_bundle, trusted_attestor_public_keys,
                       expected_authority_id, expected_registry_id,
                       expected_project_id, expected_owner_scope_sha256,
                       expected_challenge, now):
    """Return a *signed candidate* with all authority gates explicitly FALSE.

    This module does not obtain or authenticate a current remote high-water,
    consume a challenge/nonce, validate R14 HMAC, or authenticate a native owner.
    Positive structure never grants execution.
    """
    _fields(attestation, ATTEST_FIELDS, "attestation")
    if attestation["schema"] != ATTEST_SCHEMA or attestation["audience"] != AUDIENCE:
        raise ObservationRejected("unexpected signed attestation domain")
    for f in ("authority_id","key_id","registry_id","project_id","edition",
              "policy_epoch_id","r14_owner_id","m005_owner_id","r14_owner_epoch_id"):
        _name(attestation[f], f)
    for f in ("owner_work_scope_sha256","r14_policy_sha256",
              "r14_anchor_sha256","source_guard_sha256","source_capture_sha256",
              "r14_source_sha256","corpus_sha256","owner_observation_sha256",
              "nonce_sha256","m005_anchor_sha256","previous_attestation_sha256"):
        _sha(attestation[f], HEX64, f)
    _sha(attestation["m005_source_revision"], HEX40, "M005 Git revision")
    for f in ("owner_epoch_counter","fence_generation","sequence",
              "owner_observation_size_bytes"):
        _int(attestation[f], f)
    if (attestation["owner_epoch_counter"] < 1 or attestation["fence_generation"] < 1
        or attestation["sequence"] < 1):
        raise ObservationRejected("zero epoch/fence/sequence")
    if type(attestation["challenge"]) is not str or CHALLENGE.fullmatch(attestation["challenge"]) is None:
        raise ObservationRejected("invalid signed challenge")
    _highwater(independently_pinned_highwater)
    _policy(r14_signed_policy)
    _anchor14(r14_review_anchor)
    _source_guard(source_guard_review)
    _capture(source_guard_capture, source_guard_review)
    for f,v in (("expected_authority_id",expected_authority_id),
                ("expected_registry_id",expected_registry_id),
                ("expected_project_id",expected_project_id)):
        _name(v,f)
    _sha(expected_owner_scope_sha256, HEX64, "expected owner scope")
    if (type(expected_challenge) is not str or
        CHALLENGE.fullmatch(expected_challenge) is None):
        raise ObservationRejected("invalid externally expected challenge")
    moment = _now(now)
    observed = _instant(attestation["observed_utc"], "observed")
    if (observed != _instant(attestation["source_capture_finished_utc"], "signed source capture time")
        or observed != _instant(source_guard_capture["finished_utc"], "source capture finish")
        or observed > moment):
        raise ObservationRejected("attestation not time-bound to measured hash capture")
    issued = _instant(attestation["issued_utc"], "issued")
    expires = _instant(attestation["expires_utc"], "expiry")
    if (observed > issued or issued > moment + timedelta(seconds=5)
        or moment >= expires or moment < issued - timedelta(seconds=5)
        or issued - observed > timedelta(seconds=30)
        or expires - issued <= timedelta(0)
        or expires - issued > timedelta(seconds=60)):
        raise ObservationRejected("stale, future or overly broad signed window")
    if not (attestation["authority_id"] == expected_authority_id ==
            independently_pinned_highwater["authority_id"]):
        raise ObservationRejected("authority scope mismatch")
    if not (attestation["registry_id"] == expected_registry_id ==
            independently_pinned_highwater["registry_id"] ==
            r14_review_anchor["registry_id"]):
        raise ObservationRejected("registry scope mismatch")
    if (attestation["project_id"] != expected_project_id or
        attestation["project_id"] != r14_signed_policy["project_id"] or
        attestation["edition"] != r14_signed_policy["edition"] or
        attestation["r14_owner_id"] != r14_signed_policy["owner_id"] or
        attestation["r14_owner_epoch_id"] != r14_signed_policy["owner_epoch"] or
        attestation["policy_epoch_id"] != r14_signed_policy["policy_epoch"] or
        attestation["fence_generation"] != r14_signed_policy["fence_generation"] or
        attestation["owner_work_scope_sha256"] != expected_owner_scope_sha256 or
        attestation["owner_work_scope_sha256"] != r14_signed_policy["owner_work_scope_sha256"] or
        attestation["r14_source_sha256"] != r14_signed_policy["source_sha256"] or
        attestation["nonce_sha256"] != r14_signed_policy["nonce_sha256"]):
        raise ObservationRejected("R14 owner or source/scope/fence binding mismatch")
    if (attestation["challenge"] != expected_challenge or
        attestation["sequence"] != independently_pinned_highwater["sequence"] + 1 or
        attestation["previous_attestation_sha256"] != independently_pinned_highwater["last_attestation_sha256"] or
        not independently_pinned_highwater["owner_epoch_counter"] <=
            attestation["owner_epoch_counter"] <= independently_pinned_highwater["owner_epoch_counter"] + 1):
        raise ObservationRejected("stale replay, nonmonotonic head or forged challenge")
    if (attestation["r14_policy_sha256"] != sha256_json(r14_signed_policy) or
        attestation["r14_anchor_sha256"] != sha256_json(r14_review_anchor) or
        attestation["source_guard_sha256"] != sha256_json(source_guard_review) or
        attestation["source_capture_sha256"] != sha256_json(source_guard_capture) or
        attestation["owner_observation_sha256"] != source_guard_review["live_observation_captured_sha256"] or
        attestation["owner_observation_size_bytes"] != source_guard_review["live_observation_byte_count"]):
        raise ObservationRejected("source/observation payload not bound")
    if type(m005_verified_bundle) is not dict:
        raise ObservationRejected("actual M005 verification bundle missing")
    if m005_verified_bundle.get("now") != now:
        raise ObservationRejected("M005 and observation signatures checked at different times")
    try:
        m005_result = verify_detached_anchor(**m005_verified_bundle)
    except (AnchorRejected, TypeError, KeyError) as exc:
        raise ObservationRejected("M005 candidate verification failed") from exc
    if (m005_result.get("status") != "SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF" or
        m005_result.get("dispatch_authorized") is not False or
        m005_result.get("current_external_high_water_verified") is not False):
        raise ObservationRejected("M005 result is not explicitly non-authorizing")
    m005_anchor = m005_verified_bundle["anchor"]
    if _instant(m005_anchor["issued_utc"], "M005 issued") > issued:
        raise ObservationRejected("observation attestation signed before its M005 input existed")
    if (m005_anchor.get("schema") != M005_SCHEMA or
        attestation["m005_owner_id"] != m005_anchor["owner_id"] or
        attestation["m005_source_revision"] != m005_anchor["source_revision"] or
        attestation["corpus_sha256"] != m005_anchor["corpus_sha256"] or
        attestation["owner_epoch_counter"] != m005_anchor["owner_epoch"] or
        attestation["m005_anchor_sha256"] != sha256_json(m005_anchor)):
        raise ObservationRejected("M005 signed anchor not bound to observation attestation")
    _verify_signature(attestation, trusted_attestor_public_keys)
    next_head = {
        "schema": HIGHWATER_SCHEMA,
        "authority_id": attestation["authority_id"],
        "registry_id": attestation["registry_id"],
        "sequence": attestation["sequence"],
        "owner_epoch_counter": attestation["owner_epoch_counter"],
        "last_attestation_sha256": sha256_json(attestation),
    }
    return {
        "status": "SIGNED_CROSS_BOUND_REVIEW_NOT_CURRENT_OWNER_AUTHORITY",
        "schema": "ORF-M008.ObservationReviewDecision.v1",
        "signed_claim_bytes_verified": True,
        "m005_candidate_signature_verified": True,
        "source_guard_report_independently_authenticated": False,
        "source_capture_hash_bound": True,
        "source_capture_authenticated_by_independent_reader": False,
        "r14_owner_policy_mac_independently_verified": False,
        "r14_anchor_mac_independently_verified": False,
        "externally_current_highwater_verified": False,
        "challenge_single_use_verified": False,
        "numeric_epoch_to_r14_epoch_id_trusted_mapping_verified": False,
        "global_owner_scope_authority_verified": False,
        "native_cas_receipt_provenance_verified": False,
        "production_native_worker_fencing_verified": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
        "next_highwater_proposal_only": next_head,
    }
