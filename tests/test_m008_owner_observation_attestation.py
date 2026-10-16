"""Offline M008 signatures, cross-binding, replay and fail-closed fixtures."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import secrets

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from openremaster.m005_anchor_contract import sha256_json
from openremaster.m008_owner_observation_attestation import (
    ATTEST_SCHEMA, AUDIENCE, HIGHWATER_SCHEMA, ObservationRejected,
    SIGN_CONTEXT, signing_message, verify_attestation,
)
from test_m005_anchor_contract import case as m005_case, NOW, CORPUS, REVISION
from test_source_freshness_guard_v1 import fixtures as freshness_fixtures, review as freshness_review

REGISTRY = "r14-registry-test"
AUTHORITY = "independent-attestor-test"
R14_OWNER = "r14-owner-test"
R14_EPOCH = "r14-epoch-string"
WORK_SCOPE = "7" * 64
NONCE = "8" * 64


def r14_policy():
    return {
        "schema": "OpenRemaster.R13SignedOwnerModeDecision.v1",
        "audience": "ORF-HostLocal-ExclusiveNativeMode-OwnerReview-v1",
        "purpose": "EXCLUSIVE_LEGACY_OR_V2_MODE_REVIEW_ONLY",
        "mode": "V2_REQUIRED",
        "project_id": "OpenAzrael",
        "edition": "AzraelDemo",
        "job_id": "synthetic-r14-job",
        "work_identity_sha256": "1" * 64,
        "owner_work_scope_sha256": WORK_SCOPE,
        "job_sha256": "2" * 64,
        "legacy_envelope_sha256": "3" * 64,
        "source_sha256": "4" * 64,
        "checkpoint_sha256": "5" * 64,
        "nonce_sha256": NONCE,
        "owner_id": R14_OWNER,
        "owner_epoch": R14_EPOCH,
        "lease_id": "lease-R14",
        "policy_epoch": "policy-epoch-R14",
        "fence_generation": 1,
        "r5_operation_id": "synthetic-op",
        "legacy_permit_sha256": None,
        "r10_prestart_sha256": "a" * 64,
        "r6_signed_ack_sha256": "b" * 64,
        "issued_at_unix": 1791921600,
        "expires_at_unix": 1791921700,
        "mac": "c" * 64,
    }


def r14_anchor():
    return {
        "schema": "OpenRemaster.R14IndependentRegistryAnchor.v1",
        "audience": "ORF-ExternalRegistryAnchor-OwnerReviewOnly-v1",
        "registry_id": REGISTRY,
        "external_anchor_sequence": 1,
        "prior_external_anchor_sha256": "0" * 64,
        "registry_event_count": 1,
        "registry_mode_count": 1,
        "last_registry_event_sha256": "d" * 64,
        "source_registry_schema": "OpenRemaster.R13HostLocalExclusiveOwnerRegistry.v1",
        "captured_at_unix": 1791921600,
        "expires_at_unix": 1791921700,
        "signer_id": "fake-independent-R14-signer",
        "source_producer_id": "r14-worker-test",
        "mac": "e" * 64,
    }


def sample():
    policy = r14_policy()
    anchor14 = r14_anchor()
    sk, m005 = m005_case()
    review_now = NOW + timedelta(seconds=8)
    m005['now'] = review_now
    frozen, capture = freshness_fixtures()
    capture['started_utc'] = '2026-10-13T20:00:15Z'
    capture['finished_utc'] = '2026-10-13T20:00:18Z'
    report = freshness_review(frozen, capture, now=review_now)
    report["sealed_pilot_bytes_verified"] = True  # test-only claim; NOT verified by M008!
    signer = Ed25519PrivateKey.generate()
    public = signer.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    challenge = secrets.token_urlsafe(24)
    highwater = {
        "schema": HIGHWATER_SCHEMA, "authority_id": AUTHORITY,
        "registry_id": REGISTRY, "sequence": 10,
        "owner_epoch_counter": 3, "last_attestation_sha256": "f" * 64,
    }
    a = {
        "schema": ATTEST_SCHEMA, "audience": AUDIENCE,
        "authority_id": AUTHORITY, "key_id": "test-ed25519-1",
        "registry_id": REGISTRY, "project_id": policy["project_id"],
        "edition": policy["edition"], "policy_epoch_id": policy["policy_epoch"],
        "r14_owner_id": policy["owner_id"],
        "m005_owner_id": m005["anchor"]["owner_id"],
        "owner_work_scope_sha256": WORK_SCOPE,
        "r14_policy_sha256": sha256_json(policy),
        "r14_anchor_sha256": sha256_json(anchor14),
        "source_guard_sha256": sha256_json(report),
        "source_capture_sha256": sha256_json(capture),
        "source_capture_finished_utc": capture['finished_utc'],
        "r14_source_sha256": policy["source_sha256"],
        "m005_source_revision": REVISION,
        "corpus_sha256": CORPUS,
        "owner_observation_sha256": report["live_observation_captured_sha256"],
        "owner_observation_size_bytes": report["live_observation_byte_count"],
        "r14_owner_epoch_id": R14_EPOCH,
        "owner_epoch_counter": m005["anchor"]["owner_epoch"],
        "fence_generation": policy["fence_generation"],
        "nonce_sha256": NONCE,
        "m005_anchor_sha256": sha256_json(m005["anchor"]),
        "sequence": 11,
        "previous_attestation_sha256": highwater["last_attestation_sha256"],
        "challenge": challenge,
        "observed_utc": "2026-10-13T20:00:18Z",
        "issued_utc": "2026-10-13T20:00:20Z",
        "expires_utc": "2026-10-13T20:00:45Z",
        "signature_b64": "",
    }
    args = {
        "attestation": a, "independently_pinned_highwater": highwater,
        "source_guard_review": report, "source_guard_capture": capture,
        "r14_signed_policy": policy,
        "r14_review_anchor": anchor14, "m005_verified_bundle": m005,
        "trusted_attestor_public_keys": {(AUTHORITY, "test-ed25519-1"): public},
        "expected_authority_id": AUTHORITY, "expected_registry_id": REGISTRY,
        "expected_project_id": "OpenAzrael",
        "expected_owner_scope_sha256": WORK_SCOPE,
        "expected_challenge": challenge, "now": review_now,
    }
    resign(signer, args)
    return signer, args


def resign(private, args):
    args["attestation"]["signature_b64"] = base64.b64encode(
        private.sign(signing_message(args["attestation"]))
    ).decode("ascii")


def test_cross_signed_claims_still_cannot_grant_owner_authority():
    key, args = sample()
    out = verify_attestation(**args)
    assert out["status"] == "SIGNED_CROSS_BOUND_REVIEW_NOT_CURRENT_OWNER_AUTHORITY"
    assert out["signed_claim_bytes_verified"] is True
    assert out["m005_candidate_signature_verified"] is True
    assert out["dispatch_authorized"] is False
    assert out["worker_execution_authorized"] is False
    for field, value in out.items():
        if field.endswith("_verified") and field not in (
            "signed_claim_bytes_verified", "m005_candidate_signature_verified"
        ):
            assert value is False, field
    h = out["next_highwater_proposal_only"]
    assert h["schema"] == HIGHWATER_SCHEMA
    assert (h["sequence"], h["owner_epoch_counter"]) == (11, 4)
    assert h["last_attestation_sha256"] == sha256_json(args["attestation"])


def test_signature_domain_separated_from_m005_and_r14():
    _, args = sample()
    payload = signing_message(args["attestation"])
    assert payload.startswith(SIGN_CONTEXT)
    assert payload != args["m005_verified_bundle"]["anchor"]["signature_b64"].encode()
    assert b"signature_b64" not in payload
    assert b"owner_work_scope_sha256" in payload


@pytest.mark.parametrize("field", [
    "schema", "audience", "authority_id", "key_id", "registry_id",
    "project_id", "edition", "policy_epoch_id", "r14_owner_id",
    "m005_owner_id", "owner_work_scope_sha256", "r14_policy_sha256",
    "r14_anchor_sha256", "source_guard_sha256", "source_capture_sha256",
    "source_capture_finished_utc", "r14_source_sha256",
    "m005_source_revision", "corpus_sha256", "owner_observation_sha256",
    "owner_observation_size_bytes", "r14_owner_epoch_id", "owner_epoch_counter",
    "fence_generation", "nonce_sha256", "m005_anchor_sha256", "sequence",
    "previous_attestation_sha256", "challenge", "observed_utc",
    "issued_utc", "expires_utc",
])
def test_changed_field_without_resigning_is_rejected(field):
    _, args = sample()
    a = args["attestation"]
    if field in ("owner_observation_size_bytes","owner_epoch_counter",
                 "fence_generation","sequence"):
        a[field] += 1
    else:
        a[field] = "mutated-value"
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


@pytest.mark.parametrize("change", [
    "missing-key", "different-public-key", "wrong-key-id",
    "corrupt-signature", "no-padding", "wrong-short-public-key",
    "noncanonical-signature", "missing-field", "extra-field",
])
def test_signature_trust_and_fields_fail_closed(change):
    _, args = sample()
    a = args["attestation"]
    if change == "missing-key":
        args["trusted_attestor_public_keys"] = {}
    elif change == "different-public-key":
        args["trusted_attestor_public_keys"][(AUTHORITY, "test-ed25519-1")] = (
            Ed25519PrivateKey.generate().public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        )
    elif change == "wrong-key-id":
        a["key_id"] = "untrusted"
    elif change == "corrupt-signature":
        a["signature_b64"] = "not-base64!"
    elif change == "no-padding":
        a["signature_b64"] = a["signature_b64"].rstrip("=")
    elif change == "wrong-short-public-key":
        args["trusted_attestor_public_keys"][(AUTHORITY, "test-ed25519-1")] = b"not-32-byte-key"
    elif change == "noncanonical-signature":
        a["signature_b64"] += "=="
    elif change == "missing-field":
        a.pop("nonce_sha256")
    else:
        a["production_dispatch_authorized"] = True
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


@pytest.mark.parametrize("change", [
    "stale-sequence", "incorrect-previous-head", "old-counter",
    "epoch-jump", "wrong-pinned-authority", "wrong-pinned-registry",
    "boolean-pinned-sequence", "bogus-highwater-schema",
    "stale-challenge", "expected-scope", "expected-project",
])
def test_untrusted_highwater_and_expected_scope_fail_closed(change):
    _, args = sample()
    w = args["independently_pinned_highwater"]
    if change == "stale-sequence":
        w["sequence"] = 11
    elif change == "incorrect-previous-head":
        w["last_attestation_sha256"] = "a" * 64
    elif change == "old-counter":
        w["owner_epoch_counter"] = 5
    elif change == "epoch-jump":
        w["owner_epoch_counter"] = 1
    elif change == "wrong-pinned-authority":
        w["authority_id"] = "other"
    elif change == "wrong-pinned-registry":
        w["registry_id"] = "other"
    elif change == "boolean-pinned-sequence":
        w["sequence"] = True
    elif change == "bogus-highwater-schema":
        w["schema"] = "HIGHWATER.PRODUCTION_READY"
    elif change == "stale-challenge":
        args["expected_challenge"] = secrets.token_urlsafe(24)
    elif change == "expected-scope":
        args["expected_owner_scope_sha256"] = "9" * 64
    else:
        args["expected_project_id"] = "OpenOther"
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


@pytest.mark.parametrize("change", [
    "guard-fabricated-acceptance", "guard-drifts", "guard-not-sealed",
    "guard-stale", "guard-unstable", "guard-fake-pilot",
    "owner-different", "r14-hmac-mutated", "r14-policy-epoch",
    "r14-fence-mismatch", "nonce-mismatch", "r14-registry-id",
    "r14-source-sha-mismatch", "r14-anchor-self-signed",
    "r14-anchor-mac-mutated", "r14-mode-unknown",
])
def test_r14_and_source_guard_contracts_do_not_accept_mutation(change):
    key, args = sample()
    p = args["r14_signed_policy"]
    a = args["r14_review_anchor"]
    g = args["source_guard_review"]
    if change == "guard-fabricated-acceptance":
        g["dispatch_authorized"] = True
    elif change == "guard-drifts":
        g["immutable_matched_count"] = 60
    elif change == "guard-not-sealed":
        g["sealed_pilot_bytes_verified"] = False
    elif change == "guard-stale":
        g["classification"] = "CAPTURE_TIME_ASSERTION_STALE_OR_FUTURE_HOLD"
    elif change == "guard-unstable":
        g["live_observation_stable_within_read_pair"] = False
    elif change == "guard-fake-pilot":
        g["source_pilot_sha256_pinned"] = "0" * 64
    elif change == "owner-different":
        p["owner_id"] = "impostor"
    elif change == "r14-hmac-mutated":
        p["mac"] = "f" * 64
    elif change == "r14-policy-epoch":
        p["policy_epoch"] = "different"
    elif change == "r14-fence-mismatch":
        p["fence_generation"] = 2
    elif change == "nonce-mismatch":
        p["nonce_sha256"] = "f" * 64
    elif change == "r14-registry-id":
        a["registry_id"] = "different-registry"
    elif change == "r14-source-sha-mismatch":
        p["source_sha256"] = "f" * 64
    elif change == "r14-anchor-self-signed":
        a["signer_id"] = a["source_producer_id"]
    elif change == "r14-anchor-mac-mutated":
        a["mac"] = "f" * 64
    else:
        p["mode"] = "BOTH_V1_V2"
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


@pytest.mark.parametrize("change", [
    "replace-anchor-signature", "replace-m005-owner",
    "replace-m005-corpus", "wrong-m005-highwater",
    "wrong-m005-source-revision", "invalid-m005-bundle",
])
def test_m005_signature_and_content_enforced_again(change):
    _, args = sample()
    v = args["m005_verified_bundle"]
    if change == "replace-anchor-signature":
        v["anchor"]["signature_b64"] = base64.b64encode(b"0" * 64).decode()
    elif change == "replace-m005-owner":
        v["anchor"]["owner_id"] = "switched"
    elif change == "replace-m005-corpus":
        v["anchor"]["corpus_sha256"] = "f" * 64
    elif change == "wrong-m005-highwater":
        v["independent_checkpoint"]["sequence"] = 10
    elif change == "wrong-m005-source-revision":
        v["expected_source_revision"] = "b" * 40
    else:
        args["m005_verified_bundle"] = {}
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


@pytest.mark.parametrize("time_change", [
    "issued-too-old", "issued-future", "expired",
    "observation-after-issued", "observation-too-old",
    "expiry-too-long", "timezone-offset", "bad-calendar",
    "naive-now",
])
def test_time_and_clock_fail_closed(time_change):
    key, args = sample()
    a = args["attestation"]
    if time_change == "issued-too-old":
        a["issued_utc"] = "2026-10-13T19:59:00Z"
    elif time_change == "issued-future":
        a["issued_utc"] = "2026-10-13T20:00:30Z"
    elif time_change == "expired":
        a["expires_utc"] = "2026-10-13T20:00:14Z"
    elif time_change == "observation-after-issued":
        a["observed_utc"] = "2026-10-13T20:00:11Z"
    elif time_change == "observation-too-old":
        a["observed_utc"] = "2026-10-13T19:58:10Z"
    elif time_change == "expiry-too-long":
        a["expires_utc"] = "2026-10-13T20:02:40Z"
    elif time_change == "timezone-offset":
        a["observed_utc"] = "2026-10-13T22:00:00+02:00"
    elif time_change == "bad-calendar":
        a["issued_utc"] = "2026-02-30T20:00:10Z"
    else:
        args["now"] = NOW.replace(tzinfo=None)
    resign(key, args)
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


def test_valid_signature_and_forged_local_source_report_do_not_grant_owner():
    sk, args = sample()
    # This report is deliberately an IN-MEMORY claim of sealed-pilot review.
    # M008 cannot independently rerun a real HomePC file/signer attestation.
    assert args["source_guard_review"]["sealed_pilot_bytes_verified"] is True
    assert verify_attestation(**args)["source_guard_report_independently_authenticated"] is False
    assert verify_attestation(**args)["dispatch_authorized"] is False


def test_replay_of_same_signed_claim_and_old_caller_highwater_is_not_freshness():
    sk, args = sample()
    first = verify_attestation(**args)
    second = verify_attestation(**args)
    assert first == second
    assert first["externally_current_highwater_verified"] is False
    assert first["challenge_single_use_verified"] is False
    assert second["dispatch_authorized"] is False


def test_even_resigned_fake_r14_anchor_mac_cannot_make_global_authority():
    sk, args = sample()
    args["r14_review_anchor"]["mac"] = "f" * 64
    args["attestation"]["r14_anchor_sha256"] = sha256_json(args["r14_review_anchor"])
    resign(sk, args)
    result = verify_attestation(**args)
    assert result["r14_anchor_mac_independently_verified"] is False
    assert result["dispatch_authorized"] is False


def test_epoch_identifier_must_remain_distinct_from_numeric_m005_epoch():
    _, args = sample()
    a = args["attestation"]
    assert isinstance(a["r14_owner_epoch_id"], str)
    assert type(a["owner_epoch_counter"]) is int
    assert verify_attestation(**args)["numeric_epoch_to_r14_epoch_id_trusted_mapping_verified"] is False


def test_boolean_integer_coercion_is_rejected_even_if_resigned():
    sk, args = sample()
    args["attestation"]["owner_epoch_counter"] = True
    resign(sk, args)
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


def test_source_review_status_only_never_proves_external_head():
    sk, args = sample()
    result = verify_attestation(**args)
    assert result["externally_current_highwater_verified"] is False
    assert result["global_owner_scope_authority_verified"] is False
    assert result["native_cas_receipt_provenance_verified"] is False
    assert result["production_native_worker_fencing_verified"] is False


@pytest.mark.parametrize("change", [
    "missing-capture", "wrong-capture-version", "wrong-owner-first-read",
    "wrong-owner-second-read", "fake-owner-size", "oversized-static-file",
    "capture-missing-file", "capture-extra-file", "malformed-static-hash",
    "malformed-utc-finish", "reverse-window", "capture-over-a-minute",
    "not-a-dict", "capture-missing-hash", "noninteger-byte-count",
])
def test_source_hash_capture_must_be_explicitly_bound_and_well_formed(change):
    _, args = sample()
    capture = args["source_guard_capture"]
    owner = next(k for k in capture["files"] if k.endswith("interactive-runtime-owner-v12.json"))
    static = next(k for k in capture["files"] if k != owner)
    if change == "missing-capture":
        capture.pop("files")
    elif change == "wrong-capture-version":
        capture["schema"] = "FUTURE.PRODUCTION_READY"
    elif change == "wrong-owner-first-read":
        capture["files"][owner]["first_sha256"] = "9" * 64
    elif change == "wrong-owner-second-read":
        capture["files"][owner]["second_sha256"] = "9" * 64
    elif change == "fake-owner-size":
        capture["files"][owner]["byte_count"] = 999
    elif change == "oversized-static-file":
        capture["files"][static]["byte_count"] = 70000000
    elif change == "capture-missing-file":
        capture["files"].pop(static)
    elif change == "capture-extra-file":
        capture["files"]["F:\\Remaster Framework\\extra.txt"] = {
            "first_sha256": "c"*64, "second_sha256": "c"*64, "byte_count": 1
        }
    elif change == "malformed-static-hash":
        capture["files"][static]["second_sha256"] = "invalid"
    elif change == "malformed-utc-finish":
        capture["finished_utc"] = "tomorrow"
    elif change == "reverse-window":
        capture["started_utc"] = "2026-10-13T20:00:30Z"
    elif change == "capture-over-a-minute":
        capture["started_utc"] = "2026-10-13T19:58:00Z"
    elif change == "not-a-dict":
        args["source_guard_capture"] = ["untrusted"]
    elif change == "capture-missing-hash":
        capture["files"][static].pop("second_sha256")
    else:
        capture["files"][static]["byte_count"] = True
    with pytest.raises(ObservationRejected):
        verify_attestation(**args)


def test_different_now_between_m005_signature_check_and_observation_is_refused():
    sk, args = sample()
    args["m005_verified_bundle"]["now"] = NOW
    with pytest.raises(ObservationRejected, match="different times"):
        verify_attestation(**args)


def test_source_capture_forged_but_resigned_still_cannot_grant_authority():
    signer, args = sample()
    capture = args["source_guard_capture"]
    capture["started_utc"] = "2026-10-13T20:00:16Z"
    capture["finished_utc"] = "2026-10-13T20:00:19Z"
    a = args["attestation"]
    a["source_capture_finished_utc"] = capture["finished_utc"]
    a["observed_utc"] = capture["finished_utc"]
    a["source_capture_sha256"] = sha256_json(capture)
    resign(signer, args)
    result = verify_attestation(**args)
    assert result["source_capture_hash_bound"] is True
    assert result["source_capture_authenticated_by_independent_reader"] is False
    assert result["dispatch_authorized"] is False


def test_observation_attestation_cannot_be_issued_before_signed_m005_anchor():
    signer, args = sample()
    a = args["attestation"]
    # M005 original signed anchor issued at 20:00:13Z.
    a["issued_utc"] = "2026-10-13T20:00:12Z"
    a["observed_utc"] = "2026-10-13T20:00:11Z"
    a["source_capture_finished_utc"] = a["observed_utc"]
    capture = args["source_guard_capture"]
    capture["finished_utc"] = a["observed_utc"]
    capture["started_utc"] = "2026-10-13T20:00:10Z"
    a["source_capture_sha256"] = sha256_json(capture)
    resign(signer, args)
    with pytest.raises(ObservationRejected, match="before its M005 input"):
        verify_attestation(**args)
