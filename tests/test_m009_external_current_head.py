"""Synthetic current-head tests: no HomePC active owner or native worker."""
import base64
from copy import deepcopy
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from openremaster.m005_anchor_contract import sha256_json
from openremaster.m009_external_current_head import (
    SCHEMA, TrustSnapshot, SyntheticCheckpoint, HeadRejected,
    signing_message, verify_current_head,
)
from test_m008_owner_observation_attestation import sample, resign as resign_m008


def fixture(*, include_m008_signer=False):
    m008_signer, bundle = sample()
    a = bundle["attestation"]
    h = bundle["independently_pinned_highwater"]
    signer = Ed25519PrivateKey.generate()
    public = signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    r = {f: a[f] for f in (
        "authority_id", "registry_id", "project_id", "edition",
        "owner_work_scope_sha256", "challenge", "sequence",
        "owner_epoch_counter", "fence_generation", "previous_attestation_sha256")}
    r.update(schema=SCHEMA, audience="ORF-CurrentHead-ReviewOnly-v1", key_id="head-test-key",
             attestation_sha256=sha256_json(a), revocation_generation=2,
             issued_utc=a["issued_utc"], expires_utc=a["expires_utc"],
             operation="CAS_HEAD_AND_CONSUME_CHALLENGE", signature_b64="")
    # M008 window may be 60 seconds; M009 limits receipts to 30 seconds.
    from datetime import datetime, timedelta
    issued = datetime.strptime(r["issued_utc"], "%Y-%m-%dT%H:%M:%SZ")
    r["expires_utc"] = (issued + timedelta(seconds=25)).strftime("%Y-%m-%dT%H:%M:%SZ")
    args = dict(receipt=r, m008_bundle=bundle,
                trust=TrustSnapshot(a["authority_id"], {"head-test-key": public},
                                    frozenset(), 2, "2026-10-13T20:01:00Z"),
                checkpoint=SyntheticCheckpoint(tuple(a[f] for f in ("authority_id", "registry_id", "project_id", "edition", "owner_work_scope_sha256")), h["sequence"], h["owner_epoch_counter"],
                                               a["fence_generation"], h["last_attestation_sha256"], 2),
                expected_challenge=a["challenge"], now=bundle["now"], authority_available=True,
                authority_outcome="COMMIT_CONFIRMED")
    resign(signer, r)
    if include_m008_signer:
        return signer, args, m008_signer
    return signer, args


def resign(signer, r):
    r["signature_b64"] = base64.b64encode(signer.sign(signing_message(r))).decode()


def state(cp):
    return (cp.sequence, cp.epoch, cp.fence, cp.head, cp.revocation_generation,
            set(cp.consumed), cp.trust_content_sha256)


@pytest.mark.parametrize("outcome", [None, True, "UNKNOWN", "TIMEOUT", "COMMIT_REJECTED", "READ_CACHED_HEAD"])
def test_unconfirmed_outcome_never_spends_challenge(outcome):
    _, args = fixture()
    args["authority_outcome"] = outcome
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected, match="recovery required"):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


def test_lost_response_after_commit_cannot_be_guessed_or_recommitted():
    _, args = fixture()
    verify_current_head(**args)  # model server accepted, response then lost
    before = state(args["checkpoint"])
    args["authority_outcome"] = "UNKNOWN"
    with pytest.raises(HeadRejected, match="recovery required"):
        verify_current_head(**args)
    args["authority_outcome"] = "COMMIT_CONFIRMED"
    with pytest.raises(HeadRejected):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


@pytest.mark.parametrize("seconds", [22, 23, 24, 120])
def test_delayed_receipt_rejected_at_or_after_expiry(seconds):
    from datetime import timedelta
    _, args = fixture()
    # Fixture now is 20:00:23Z, receipt expiry is 20:00:45Z.
    moment = args["now"] + timedelta(seconds=seconds)
    args["now"] = moment
    args["m008_bundle"]["now"] = moment
    args["m008_bundle"]["m005_verified_bundle"]["now"] = moment
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected, match="receipt window|stale revocation"):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


def test_caller_mutation_after_signature_check_cannot_change_committed_head(monkeypatch):
    import openremaster.m009_external_current_head as module
    _, args = fixture()
    original_verify = module.verify_attestation
    signed_head = args["receipt"]["attestation_sha256"]
    def mutate_callers_evidence(**bundle):
        result = original_verify(**bundle)
        # Simulate another caller changing the original structures while validation runs.
        args["m008_bundle"]["attestation"]["r14_source_sha256"] = "e" * 64
        args["receipt"]["attestation_sha256"] = sha256_json(args["m008_bundle"]["attestation"])
        args["trust"].keys.clear()
        return result
    monkeypatch.setattr(module, "verify_attestation", mutate_callers_evidence)
    assert verify_current_head(**args)["dispatch_authorized"] is False
    assert args["checkpoint"].head == signed_head
    assert args["checkpoint"].head != args["receipt"]["attestation_sha256"]

def test_positive_still_never_authorizes():
    _, args = fixture()
    result = verify_current_head(**args)
    assert result["receipt_signature_verified"] is True
    for f in ("dispatch_authorized", "worker_execution_authorized",
              "external_current_head_independently_verified",
              "durable_global_challenge_consumption_verified",
              "current_external_revocation_verified", "rollback_resistance_verified"):
        assert result[f] is False


def test_same_receipt_replay_rejected():
    _, args = fixture()
    verify_current_head(**args)
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


def successor(signer, args, m008_signer, *, challenge):
    """Build a genuinely valid next M008/M009 head, sharing only checkpoint."""
    next_args = dict(args)
    next_args["m008_bundle"] = deepcopy(args["m008_bundle"])
    next_args["receipt"] = deepcopy(args["receipt"])
    cp = args["checkpoint"]
    bundle = next_args["m008_bundle"]
    h = bundle["independently_pinned_highwater"]
    h.update(sequence=cp.sequence, owner_epoch_counter=cp.epoch,
             last_attestation_sha256=cp.head)
    a = bundle["attestation"]
    a.update(sequence=cp.sequence + 1, previous_attestation_sha256=cp.head,
             challenge=challenge)
    bundle["expected_challenge"] = challenge
    next_args["expected_challenge"] = challenge
    resign_m008(m008_signer, bundle)
    next_args["receipt"].update(sequence=a["sequence"],
        previous_attestation_sha256=cp.head, challenge=challenge,
        attestation_sha256=sha256_json(a))
    resign(signer, next_args["receipt"])
    return next_args


def test_two_sequential_heads_advance_without_authorization():
    signer, args, m008_signer = fixture(include_m008_signer=True)
    verify_current_head(**args)
    nxt = successor(signer, args, m008_signer, challenge="FreshSuccessorChallenge_0123456789")
    result = verify_current_head(**nxt)
    assert args["checkpoint"].sequence == args["receipt"]["sequence"] + 1
    assert len(args["checkpoint"].consumed) == 2
    assert result["dispatch_authorized"] is False


def test_reused_challenge_rejected_even_with_valid_successor_head():
    signer, args, m008_signer = fixture(include_m008_signer=True)
    verify_current_head(**args)
    nxt = successor(signer, args, m008_signer, challenge=args["expected_challenge"])
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected, match="consumed challenge"):
        verify_current_head(**nxt)
    assert state(args["checkpoint"]) == before


def test_key_rotation_with_generation_advance_and_old_key_revocation():
    signer, args, m008_signer = fixture(include_m008_signer=True)
    verify_current_head(**args)
    nxt = successor(signer, args, m008_signer, challenge="RotatedSuccessorChallenge_0123456789")
    new_signer = Ed25519PrivateKey.generate()
    public = new_signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    nxt["trust"] = replace(args["trust"], keys={"rotated-key": public},
        revoked_key_ids=frozenset({"head-test-key"}), generation=3)
    nxt["receipt"].update(key_id="rotated-key", revocation_generation=3)
    resign(new_signer, nxt["receipt"])
    assert verify_current_head(**nxt)["dispatch_authorized"] is False
    assert args["checkpoint"].revocation_generation == 3


@pytest.mark.parametrize("change", ["replace-key", "add-key", "add-revocation"])
def test_same_generation_trust_equivocation_rejected(change):
    signer, args, m008_signer = fixture(include_m008_signer=True)
    verify_current_head(**args)
    nxt = successor(signer, args, m008_signer, challenge="EquivocationChallenge_0123456789")
    if change == "add-revocation":
        nxt["trust"] = replace(args["trust"], revoked_key_ids=frozenset({"another-key"}))
    else:
        new_signer = Ed25519PrivateKey.generate()
        public = new_signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        keys = dict(args["trust"].keys)
        if change == "replace-key":
            keys["head-test-key"] = public
            resign(new_signer, nxt["receipt"])
        else:
            keys["additional-key"] = public
        nxt["trust"] = replace(args["trust"], keys=keys)
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected, match="without generation advance"):
        verify_current_head(**nxt)
    assert state(args["checkpoint"]) == before


@pytest.mark.parametrize("change", ["bad-digest", "malformed-key", "bad-revocation-id"])
def test_malformed_trust_content_fails_without_commit(change):
    _, args = fixture()
    if change == "bad-digest":
        args["checkpoint"].trust_content_sha256 = "invalid"
    elif change == "malformed-key":
        args["trust"] = replace(args["trust"], keys={"other-key": b"bad"})
    else:
        args["trust"] = replace(args["trust"], revoked_key_ids=frozenset({False}))
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before



def test_atomic_concurrent_replay_one_winner():
    _, args = fixture()
    def attempt(_):
        try:
            verify_current_head(**args)
            return True
        except HeadRejected:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(16))) == 1


@pytest.mark.parametrize("field,value", [
    ("sequence", 0), ("sequence", True), ("sequence", 100),
    ("owner_epoch_counter", 0), ("owner_epoch_counter", 100),
    ("fence_generation", 0), ("revocation_generation", 1),
    ("previous_attestation_sha256", "e"*64), ("attestation_sha256", "f"*64),
    ("challenge", "x"*32), ("authority_id", "wrong"), ("registry_id", "wrong"),
    ("project_id", "wrong"), ("edition", "wrong"),
    ("owner_work_scope_sha256", "f"*64),
    ("issued_utc", "2026-10-13T20:00:59Z"),
    ("expires_utc", "2026-10-13T19:59:00Z"),
    ("expires_utc", "2026-10-13T20:05:00Z"),
    ("schema", "other"), ("audience", "Execute"),
    ("operation", "READ_CACHED_HEAD"),
])
def test_resigned_invalid_receipts_fail_without_state_change(field, value):
    signer, args = fixture()
    args["receipt"][field] = value
    resign(signer, args["receipt"])
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


@pytest.mark.parametrize("change", [
    "revoked", "unknown", "stale-view", "generation-rollback", "missing-trust",
    "partition", "timeout", "bad-signature", "missing-field", "extra-field",
    "wrong-clock", "forged-m008", "stale-checkpoint", "fence-rollback",
    "epoch-rollback", "consumed", "wrong-scope", "bool-checkpoint",
])
def test_negative_trust_partition_and_monotonicity(change):
    _, args = fixture()
    trust = args["trust"]
    cp = args["checkpoint"]
    if change == "revoked":
        args["trust"] = replace(trust, revoked_key_ids=frozenset({"head-test-key"}))
    elif change == "unknown":
        args["trust"] = replace(trust, keys={})
    elif change == "stale-view":
        args["trust"] = replace(trust, expires_utc="2026-10-13T20:00:00Z")
    elif change == "generation-rollback":
        cp.revocation_generation = 3
    elif change == "missing-trust":
        args["trust"] = None
    elif change == "partition":
        args["authority_available"] = False
    elif change == "timeout":
        args["authority_available"] = None
    elif change == "bad-signature":
        args["receipt"]["signature_b64"] = base64.b64encode(b"x"*64).decode()
    elif change == "missing-field":
        args["receipt"].pop("sequence")
    elif change == "extra-field":
        args["receipt"]["dispatch_authorized"] = True
    elif change == "wrong-clock":
        args["m008_bundle"]["now"] = None
    elif change == "forged-m008":
        args["m008_bundle"]["attestation"]["signature_b64"] = base64.b64encode(b"x"*64).decode()
    elif change == "stale-checkpoint":
        cp.head = "e"*64
    elif change == "fence-rollback":
        cp.fence += 1
    elif change == "epoch-rollback":
        cp.epoch += 1
    elif change == "wrong-scope":
        cp.scope = ("other",)
    elif change == "consumed":
        cp.consumed.add(args["expected_challenge"])
    else:
        cp.sequence = True
    before = state(cp)
    with pytest.raises(HeadRejected):
        verify_current_head(**args)
    assert state(cp) == before


def test_restart_limitation_is_explicit():
    # A fresh local checkpoint can accept the same receipt: NOT global anti-replay.
    _, args = fixture()
    cp = args["checkpoint"]
    reset = SyntheticCheckpoint(cp.scope, cp.sequence, cp.epoch, cp.fence, cp.head, cp.revocation_generation)
    verify_current_head(**args)
    args["checkpoint"] = reset
    assert verify_current_head(**args)["rollback_resistance_verified"] is False


@pytest.mark.parametrize("field", [
    "sequence", "owner_epoch_counter", "fence_generation", "revocation_generation",
])
def test_wire_counter_overflow_rejected_before_commit(field):
    signer, args = fixture()
    args["receipt"][field] = 9223372036854775001
    resign(signer, args["receipt"])
    before = state(args["checkpoint"])
    with pytest.raises(HeadRejected, match="wire bound"):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


@pytest.mark.parametrize("spent", [None, [], frozenset(), {"invalid!"}, {True}])
def test_malformed_consumption_checkpoint_fails_closed(spent):
    _, args = fixture()
    cp = args["checkpoint"]
    cp.consumed = spent
    before = (cp.sequence, cp.epoch, cp.fence, cp.head, cp.revocation_generation)
    with pytest.raises(HeadRejected, match="consumed-challenge checkpoint"):
        verify_current_head(**args)
    assert (cp.sequence, cp.epoch, cp.fence, cp.head, cp.revocation_generation) == before
    assert cp.consumed is spent


def competing_candidate(signer, args, m008_signer):
    other = dict(args)
    other["receipt"] = deepcopy(args["receipt"])
    other["m008_bundle"] = deepcopy(args["m008_bundle"])
    challenge = "DifferentCandidateChallenge_0123456789"
    other["expected_challenge"] = challenge
    other["m008_bundle"]["expected_challenge"] = challenge
    other["m008_bundle"]["attestation"]["challenge"] = challenge
    resign_m008(m008_signer, other["m008_bundle"])
    other["receipt"]["challenge"] = challenge
    other["receipt"]["attestation_sha256"] = sha256_json(other["m008_bundle"]["attestation"])
    resign(signer, other["receipt"])
    return other


def test_competing_candidate_is_individually_valid():
    signer, args, m008_signer = fixture(include_m008_signer=True)
    other = competing_candidate(signer, args, m008_signer)
    assert verify_current_head(**other)["receipt_signature_verified"] is True


def test_two_different_signed_candidates_cannot_fork_same_head():
    signer, args, m008_signer = fixture(include_m008_signer=True)
    other = competing_candidate(signer, args, m008_signer)
    def attempt(bundle):
        try:
            verify_current_head(**bundle)
            return True
        except HeadRejected:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt, [args, other])) == 1
    cp = args["checkpoint"]
    assert cp.sequence == args["receipt"]["sequence"]
    assert len(cp.consumed) == 1
    assert cp.head in {args["receipt"]["attestation_sha256"], other["receipt"]["attestation_sha256"]}


def test_partition_does_not_spend_challenge_and_recovery_accepts_once():
    _, args = fixture()
    before = state(args["checkpoint"])
    args["authority_available"] = False
    with pytest.raises(HeadRejected, match="partition"):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before
    args["authority_available"] = True
    assert verify_current_head(**args)["dispatch_authorized"] is False
    with pytest.raises(HeadRejected):
        verify_current_head(**args)


def test_revocation_received_after_partition_prevents_retry():
    _, args = fixture()
    before = state(args["checkpoint"])
    args["authority_available"] = False
    with pytest.raises(HeadRejected):
        verify_current_head(**args)
    args["authority_available"] = True
    args["trust"] = replace(args["trust"], revoked_key_ids=frozenset({"head-test-key"}))
    with pytest.raises(HeadRejected, match="revoked signer"):
        verify_current_head(**args)
    assert state(args["checkpoint"]) == before


