"""M008 dual-signer review-only contract tests: all test keys ephemeral."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import secrets

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from openremaster.owner_observation_attestation_v1 import (
    ObservationRejected, OWNER_SCHEMA, HEAD_SCHEMA, PIN_SCHEMA,
    EXPECT_SCHEMA, OWNER_SIGN_CONTEXT, HEAD_SIGN_CONTEXT,
    canonical_json, sha256_json, owner_signing_message,
    head_signing_message, verify_dual_attestation, classify_external_availability,
)
from openremaster.source_freshness_guard_v1 import PINNED_R14_PILOT_SHA256

NOW = datetime(2026, 10, 14, 8, 0, 10, tzinfo=timezone.utc)
SCOPE = "d" * 64
OBS = "c" * 64
CORPUS = "a" * 64
SOURCE = "e" * 64
REQUEST = "f" * 64
COMMIT = "a" * 40
OWNER_AUTH = "owner-authority"
HEAD_AUTH = "independent-head"


def stamp(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def resign(key, record, maker):
    record["signature_b64"] = base64.b64encode(key.sign(maker(record))).decode("ascii")


def case():
    owner_key = Ed25519PrivateKey.generate()
    head_key = Ed25519PrivateKey.generate()
    owner_pk = owner_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    head_pk = head_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    challenge = secrets.token_urlsafe(24)
    assert len(challenge) >= 22
    pinned = {
        "schema": PIN_SCHEMA, "authority_id": HEAD_AUTH,
        "namespace": "OpenAzraelDemo", "sequence": 8,
        "fence_generation": 12, "last_head_sha256": "b" * 64,
    }
    owner = {
        "schema": OWNER_SCHEMA, "authority_id": OWNER_AUTH,
        "key_id": "owner-test-key", "namespace": "OpenAzraelDemo",
        "job_id": "synthetic-job", "attempt_id": "synthetic-attempt",
        "owner_id": "synthetic-owner", "worker_id": "synthetic-worker",
        "owner_epoch_label": "reviewOwnerEpochSynthetic",
        "fence_generation": 13, "owner_work_scope_sha256": SCOPE,
        "source_sha256": SOURCE, "source_git_revision": COMMIT,
        "corpus_sha256": CORPUS, "request_sha256": REQUEST,
        "observation_sha256": OBS,
        "r14_frozen_pilot_sha256": PINNED_R14_PILOT_SHA256,
        "challenge": challenge,
        "issued_utc": "2026-10-14T08:00:00Z",
        "expires_utc": "2026-10-14T08:00:40Z",
        "signature_b64": "",
    }
    resign(owner_key, owner, owner_signing_message)
    head = {
        "schema": HEAD_SCHEMA, "authority_id": HEAD_AUTH,
        "key_id": "head-test-key", "namespace": owner["namespace"],
        "sequence": 9, "previous_head_sha256": pinned["last_head_sha256"],
        "owner_attestation_sha256": sha256_json(owner),
        "job_id": owner["job_id"],
        "owner_epoch_label": owner["owner_epoch_label"],
        "fence_generation": owner["fence_generation"],
        "owner_work_scope_sha256": SCOPE,
        "observation_sha256": OBS,
        "source_git_revision": COMMIT, "corpus_sha256": CORPUS,
        "request_sha256": REQUEST, "challenge": challenge,
        "issued_utc": "2026-10-14T08:00:01Z",
        "expires_utc": "2026-10-14T08:00:39Z",
        "signature_b64": "",
    }
    resign(head_key, head, head_signing_message)
    expected = {
        "schema": EXPECT_SCHEMA,
        "namespace": owner["namespace"], "job_id":owner["job_id"],
        "attempt_id":owner["attempt_id"], "owner_id":owner["owner_id"],
        "worker_id":owner["worker_id"],
        "owner_authority_id":owner["authority_id"],
        "head_authority_id":head["authority_id"],
        "owner_work_scope_sha256":SCOPE, "source_sha256":SOURCE,
        "source_git_revision":COMMIT, "corpus_sha256":CORPUS,
        "request_sha256":REQUEST, "observation_sha256":OBS,
        "challenge":challenge,
    }
    source_review = {
        "status":"SOURCE_FRESHNESS_REVIEW_ONLY_HOLD",
        "source_pilot_sha256_pinned":PINNED_R14_PILOT_SHA256,
        "sealed_pilot_bytes_verified":True,
        "immutable_matched_count":61,
        "immutable_source_drift_paths":[],
        "live_observation_stable_within_read_pair":True,
        "current_owner_authority_verified":False,
        "dispatch_authorized":False,
        "worker_execution_authorized":False,
        "legacy_r14_full_acceptance_reclassified_as_pass":False,
        "classification":"LIVE_OWNER_OBSERVATION_CHANGED_UNATTESTED_HOLD",
        "live_observation_captured_sha256":OBS,
    }
    params = {
        "owner":owner, "head":head, "pinned_head":pinned,
        "independent_expectations":expected,
        "source_freshness_review":source_review,
        "pinned_public_keys":{
            ("owner",OWNER_AUTH,"owner-test-key"):owner_pk,
            ("head",HEAD_AUTH,"head-test-key"):head_pk,
        }, "now":NOW,
    }
    return owner_key, head_key, params


def verify(params):
    return verify_dual_attestation(**params)


def test_both_valid_detached_signatures_are_review_only():
    _, _, data = case()
    result = verify(data)
    assert result["status"] == "TWO_SIGNATURES_STRUCTURALLY_VALID_NOT_CURRENT_AUTHORITY"
    assert result["signer_roles_cryptographically_distinct"] is True
    assert result["next_head_proposal_only"]["sequence"] == 9
    assert result["next_head_proposal_only"]["fence_generation"] == 13
    assert result["next_head_proposal_only"]["last_head_sha256"] == sha256_json(data["head"])
    for k in (
        "observation_content_verified_against_live_owner",
        "source_review_origin_authenticated", "current_external_highwater_verified",
        "owner_epoch_cross_domain_mapped", "owner_work_scope_resolver_authenticated",
        "external_challenge_uniqueness_verified", "durable_nonce_spend_verified",
        "owner_cas_receipt_verified", "worker_side_fence_verified",
        "production_owner_authorized", "dispatch_authorized",
        "worker_execution_authorized",
    ):
        assert result[k] is False


def test_distinct_signing_domains_and_python_json_canonicalization():
    _, _, p = case()
    assert owner_signing_message(p["owner"]).startswith(OWNER_SIGN_CONTEXT)
    assert head_signing_message(p["head"]).startswith(HEAD_SIGN_CONTEXT)
    assert OWNER_SIGN_CONTEXT != HEAD_SIGN_CONTEXT
    assert canonical_json({"č":1,"n":2}) == canonical_json({"n":2,"č":1})


@pytest.mark.parametrize("field,mutated", [
    ("owner_epoch_label", "untrusted-epoch"),("owner_work_scope_sha256", "0"*64),
    ("observation_sha256", "0"*64),("source_sha256", "0"*64),
    ("source_git_revision", "0"*40),("corpus_sha256", "0"*64),
    ("request_sha256", "0"*64),("owner_id", "imposter-owner"),
    ("job_id", "imposter-job"),("attempt_id", "imposter-attempt"),
    ("worker_id", "imposter-worker"),("namespace","other-namespace"),
    ("challenge", "z"*32),("fence_generation",18),
    ("r14_frozen_pilot_sha256","0"*64),
    ("issued_utc","2026-10-14T08:00:02Z"),
    ("expires_utc","2026-10-14T08:01:00Z"),
    ("authority_id","fake-owner"),("key_id","fake-key"),
    ("schema","OwnerObservationFuture"),
])
def test_owner_mutation_after_signature_rejected(field, mutated):
    _, _, p = case()
    p["owner"][field] = mutated
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("field,mutated", [
    ("sequence",10),("previous_head_sha256","f"*64),
    ("owner_attestation_sha256","0"*64),("owner_epoch_label","otherEpoch"),
    ("fence_generation",14),("owner_work_scope_sha256","0"*64),
    ("observation_sha256","e"*64),("source_git_revision","b"*40),
    ("corpus_sha256","f"*64),("request_sha256","a"*64),
    ("challenge","w"*32),("namespace","wrongName"),("job_id","wrongJob"),
    ("issued_utc","2026-10-14T08:00:02Z"),
    ("expires_utc","2026-10-14T08:00:38Z"),
    ("schema","UnknownHead"),("authority_id","unknownHead"),
    ("key_id","unknownKey"),
])
def test_head_mutation_after_signature_rejected(field, mutated):
    _, _, p = case()
    p["head"][field] = mutated
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("field,new", [
    ("sequence",9),("fence_generation",13),
    ("last_head_sha256","a"*64),("authority_id","differentAuthority"),
    ("namespace","anotherNamespace"),("schema","OtherVersion"),
])
def test_pinned_old_head_cannot_be_substituted(field,new):
    _, _, p = case()
    p["pinned_head"][field] = new
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("field,new", [
    ("observation_sha256","a"*64),("owner_work_scope_sha256","f"*64),
    ("source_sha256","a"*64),("source_git_revision","b"*40),
    ("corpus_sha256","b"*64),("request_sha256","0"*64),
    ("namespace","other-namespace"),("job_id","other-job"),
    ("owner_id","other-owner"),("worker_id","other-worker"),
    ("attempt_id","other-attempt"),("challenge","z"*32),
    ("owner_authority_id","other-authority"),
    ("head_authority_id","other-head"),
])
def test_independent_expectation_mismatch(field,new):
    _, _, p = case()
    p["independent_expectations"][field] = new
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("fault", [
    "no-owner", "no-head", "owner-other", "head-other",
    "same-key", "wrong-owner-key", "wrong-head-key",
    "owner-bad-signature","head-bad-signature",
    "owner-noncanonical","head-noncanonical","owner-shortkey","head-shortkey",
])
def test_key_confusion_and_signature_fail_closed(fault):
    sk, hk, p = case()
    keys = p["pinned_public_keys"]
    ko = ("owner",OWNER_AUTH,"owner-test-key")
    kh = ("head",HEAD_AUTH,"head-test-key")
    if fault == "no-owner": keys.pop(ko)
    elif fault == "no-head": keys.pop(kh)
    elif fault == "owner-other": keys[("head",OWNER_AUTH,"owner-test-key")] = keys.pop(ko)
    elif fault == "head-other": keys[("owner",HEAD_AUTH,"head-test-key")] = keys.pop(kh)
    elif fault == "same-key": keys[kh] = keys[ko]
    elif fault == "wrong-owner-key": keys[ko] = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    elif fault == "wrong-head-key": keys[kh] = Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    elif fault == "owner-bad-signature": p["owner"]["signature_b64"] = base64.b64encode(Ed25519PrivateKey.generate().sign(owner_signing_message(p["owner"]))).decode()
    elif fault == "head-bad-signature": p["head"]["signature_b64"] = base64.b64encode(Ed25519PrivateKey.generate().sign(head_signing_message(p["head"]))).decode()
    elif fault == "owner-noncanonical": p["owner"]["signature_b64"] += "=="
    elif fault == "head-noncanonical": p["head"]["signature_b64"] += "=="
    elif fault == "owner-shortkey": keys[ko] = b"short"
    else: keys[kh] = b"short"
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("fault", [
    "expired-owner","expired-head","future-owner","future-head",
    "owner-over-60","head-over-60","head-before-owner",
    "head-after-owner","naive-now","stale-now","future-now",
])
def test_temporal_authority_limits(fault):
    sk, hk, p = case()
    owner, head = p["owner"], p["head"]
    if fault == "expired-owner":
        owner["expires_utc"] = "2026-10-14T08:00:09Z"
    elif fault == "expired-head":
        head["expires_utc"] = "2026-10-14T08:00:09Z"
    elif fault == "future-owner":
        owner["issued_utc"] = "2026-10-14T08:00:11Z"
    elif fault == "future-head":
        head["issued_utc"] = "2026-10-14T08:00:11Z"
    elif fault == "owner-over-60":
        owner["expires_utc"] = "2026-10-14T08:01:30Z"
    elif fault == "head-over-60":
        head["expires_utc"] = "2026-10-14T08:01:30Z"
    elif fault == "head-before-owner":
        head["issued_utc"] = "2026-10-14T07:59:59Z"
    elif fault == "head-after-owner":
        head["expires_utc"] = "2026-10-14T08:00:41Z"
    elif fault == "naive-now":
        p["now"] = NOW.replace(tzinfo=None)
    elif fault == "stale-now":
        p["now"] = NOW + timedelta(minutes=10)
    else:
        p["now"] = NOW - timedelta(minutes=10)
    resign(sk, owner, owner_signing_message)
    head["owner_attestation_sha256"] = sha256_json(owner)
    resign(hk, head, head_signing_message)
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("fault", [
    "missing-review","fake-seal","wrong-frozen","immutable-drift",
    "live-race","observation-mismatch","relabel-r14","owner-authorized",
    "dispatch-authorized","worker-authorized","review-status",
    "review-currentness-claimed","review-unknown-classification",
])
def test_r14_source_freshness_is_not_self_authenticated(fault):
    _, _, p = case()
    r = p["source_freshness_review"]
    if fault == "missing-review": p["source_freshness_review"] = None
    elif fault == "fake-seal": r["sealed_pilot_bytes_verified"] = False
    elif fault == "wrong-frozen": r["source_pilot_sha256_pinned"] = "0"*64
    elif fault == "immutable-drift": r["immutable_matched_count"] = 60
    elif fault == "live-race": r["live_observation_stable_within_read_pair"] = False
    elif fault == "observation-mismatch": r["live_observation_captured_sha256"] = "0"*64
    elif fault == "relabel-r14": r["legacy_r14_full_acceptance_reclassified_as_pass"] = True
    elif fault == "owner-authorized": r["current_owner_authority_verified"] = True
    elif fault == "dispatch-authorized": r["dispatch_authorized"] = True
    elif fault == "worker-authorized": r["worker_execution_authorized"] = True
    elif fault == "review-status": r["status"] = "PASS"
    elif fault == "review-currentness-claimed": r["immutable_source_drift_paths"] = ["untrusted"]
    else: r["classification"] = "LIVE_OWNER_AUTHORIZED"
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("fault", [
    "owner-extra-field","head-extra-field","missing-head-field",
    "owner-bool-epoch","head-bool-sequence","head-bool-fence",
    "head-negative","pinned-bool","pinned-missing",
    "expectations-extra","owner-invalid-r14-epoch",
    "owner-invalid-source-hex","head-invalid-corpus-hex",
    "owner-blank-challenge","head-blank-challenge",
])
def test_malformed_unsigned_or_signed_inputs_fail_closed(fault):
    _, _, p = case()
    a, h, pin, e = p["owner"],p["head"],p["pinned_head"],p["independent_expectations"]
    if fault == "owner-extra-field": a["safe_to_execute"] = True
    elif fault == "head-extra-field": h["safe_to_execute"] = True
    elif fault == "missing-head-field": h.pop("owner_attestation_sha256")
    elif fault == "owner-bool-epoch": a["fence_generation"] = True
    elif fault == "head-bool-sequence": h["sequence"] = True
    elif fault == "head-bool-fence": h["fence_generation"] = True
    elif fault == "head-negative": h["sequence"] = -1
    elif fault == "pinned-bool": pin["sequence"] = True
    elif fault == "pinned-missing": pin.pop("last_head_sha256")
    elif fault == "expectations-extra": e["production_ready"] = True
    elif fault == "owner-invalid-r14-epoch": a["owner_epoch_label"] = " "
    elif fault == "owner-invalid-source-hex": a["source_sha256"] = "g"*64
    elif fault == "head-invalid-corpus-hex": h["corpus_sha256"] = "g"*64
    elif fault == "owner-blank-challenge": a["challenge"] = ""
    else: h["challenge"] = ""
    with pytest.raises(ObservationRejected):
        verify(p)


@pytest.mark.parametrize("fault", [
    "changed-head-epoch","changed-head-scope","changed-head-owner",
    "changed-head-corpus","changed-head-request",
    "changed-head-observation","changed-head-revision",
    "changed-head-challenge","changed-head-sequence",
    "changed-head-parent","changed-head-owner-digest",
])
def test_validly_resigned_wrong_cross_binding_still_rejected(fault):
    sk, hk, p = case()
    h = p["head"]
    if fault == "changed-head-epoch": h["fence_generation"] = 14
    elif fault == "changed-head-scope": h["owner_work_scope_sha256"] = "f"*64
    elif fault == "changed-head-owner": h["owner_epoch_label"] = "anotherEpoch"
    elif fault == "changed-head-corpus": h["corpus_sha256"] = "f"*64
    elif fault == "changed-head-request": h["request_sha256"] = "b"*64
    elif fault == "changed-head-observation": h["observation_sha256"] = "b"*64
    elif fault == "changed-head-revision": h["source_git_revision"] = "b"*40
    elif fault == "changed-head-challenge": h["challenge"] = "a"*32
    elif fault == "changed-head-sequence": h["sequence"] = 12
    elif fault == "changed-head-parent": h["previous_head_sha256"] = "e"*64
    else: h["owner_attestation_sha256"] = "e"*64
    resign(hk, h, head_signing_message)
    with pytest.raises(ObservationRejected):
        verify(p)


def test_valid_signed_pair_and_old_pinned_head_cannot_prove_latest_remotely():
    sk, hk, p = case()
    # Attacker can replay a formerly valid signed packet and an old checkpoint
    # if it controls both inputs. The verifier must never declare current head.
    old_bundle = deepcopy(p)
    first = verify(old_bundle)
    second = verify(old_bundle)
    assert first == second
    assert second["current_external_highwater_verified"] is False
    assert second["external_challenge_uniqueness_verified"] is False
    assert second["dispatch_authorized"] is False


def test_signatures_dont_authenticate_caller_forged_r14_review():
    _, _, p = case()
    fake = dict(p["source_freshness_review"])
    assert fake["sealed_pilot_bytes_verified"] is True
    # In real deployments a trusted source sampler must produce/attest this.
    # Merely returning a structurally matching dict is not origin evidence.
    p["source_freshness_review"] = fake
    result = verify(p)
    assert result["source_review_origin_authenticated"] is False
    assert result["observation_content_verified_against_live_owner"] is False


@pytest.mark.parametrize("value", ["ONLINE","TIMEOUT","PARTITIONED","UNKNOWN","STALE"])
def test_external_availability_is_never_authorization(value):
    result = classify_external_availability(value)
    assert result["current_external_highwater_verified"] is False
    assert result["dispatch_authorized"] is False
    assert result["worker_execution_authorized"] is False


@pytest.mark.parametrize("value", [None,True,"CONNECTED","AUTHENTICATED",0,[],{}])
def test_unknown_network_observation_rejected(value):
    with pytest.raises(ObservationRejected):
        classify_external_availability(value)


def test_json_nan_and_noncanonical_bytes_rejected():
    with pytest.raises(ObservationRejected):
        canonical_json({"x":float("nan")})
    with pytest.raises(ObservationRejected):
        canonical_json({"x":object()})
