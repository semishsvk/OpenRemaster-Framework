"""ORCH-M006 pure crosswalk rejection fixtures. No signer or native execution."""
from __future__ import annotations

from copy import deepcopy
import pytest

from openremaster.m006_r14_m005_gap import (
    ContractGapRejected, GAPS, M006_SCHEMA, diagnose_review_gap,
)


def fixture():
    return {
        "r14_decision": {
            "schema": "OpenRemaster.R14RegistryExternalAnchorDecision.v1",
            "status": "SIGNED_HOSTLOCAL_REGISTRY_MATCHES_EXTERNAL_REVIEW_ANCHOR",
            "host_local_only": True,
            "real_external_anchor_authority_installed": False,
            "global_consensus_proven": False,
            "native_worker_job_dispatched": False,
            "original_gameplay_fidelity_verified": False,
        },
        "r14_anchor": {
            "schema": "OpenRemaster.R14IndependentRegistryAnchor.v1",
            "audience": "ORF-ExternalRegistryAnchor-OwnerReviewOnly-v1",
            "registry_id": "SyntheticHostLocalOwnerRegistryR14",
            "external_anchor_sequence": 1,
            "prior_external_anchor_sha256": "0" * 64,
            "registry_event_count": 1,
            "registry_mode_count": 1,
            "last_registry_event_sha256": "a" * 64,
            "source_registry_schema": "OpenRemaster.R13HostLocalExclusiveOwnerRegistry.v1",
            "captured_at_unix": 1030,
            "expires_at_unix": 1100,
            "signer_id": "independentFakeAnchorSigner",
            "source_producer_id": "localRegistryWorkerTest",
            "mac": "b" * 64,
        },
        "r14_signed_owner_mode": {
            "schema": "OpenRemaster.R13SignedOwnerModeDecision.v1",
            "mode": "V2_REQUIRED",
            "owner_work_scope_sha256": "c" * 64,
            "source_sha256": "d" * 64,
            "owner_epoch": "syntheticOwnerEpoch01",
        },
        "m005_result": {
            "status": "SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF",
            "dispatch_authorized": False,
            "worker_execution_authorized": False,
            "current_external_high_water_verified": False,
            "independent_owner_cas_authenticity_verified": False,
            "next_checkpoint_proposal_only": {
                "schema": "ORCH-M005.PinnedHighWater.v0",
                "owner_epoch": 4,
                "store_revision": 5,
            },
        },
        "m005_anchor": {
            "schema": "ORCH-M005.SignedAnchor.v0",
            "phase": "COMMITTED",
            "source_revision": "a" * 40,
            "corpus_sha256": "f" * 64,
            "owner_epoch": 4,
            "store_revision": 5,
            "sequence": 5,
        },
    }


def test_positive_review_states_are_still_not_owner_admission():
    result = diagnose_review_gap(**fixture())
    assert result["schema"] == M006_SCHEMA
    assert result["status"] == "HOLD_INCOMPATIBLE_TRUST_DOMAINS"
    assert result["gaps"] == list(GAPS)
    for field in (
        "global_owner_authority_verified", "current_external_high_water_verified",
        "r14_m005_epoch_mapping_verified", "owner_work_scope_binding_verified",
        "source_revision_mapping_verified", "native_cas_receipt_provenance_verified",
        "worker_side_fencing_verified", "dispatch_authorized",
        "worker_execution_authorized",
    ):
        assert result[field] is False


def test_legacy_review_mode_is_also_never_authority():
    data = fixture()
    data["r14_signed_owner_mode"]["mode"] = "LEGACY_V1_ALLOWED"
    assert diagnose_review_gap(**data)["dispatch_authorized"] is False


def test_r14_owner_epoch_is_string_while_m005_is_integer():
    data = fixture()
    assert type(data["r14_signed_owner_mode"]["owner_epoch"]) is str
    assert type(data["m005_anchor"]["owner_epoch"]) is int
    assert diagnose_review_gap(**data)["r14_m005_epoch_mapping_verified"] is False


def test_r14_source_hash_not_gitrevision():
    data = fixture()
    assert len(data["r14_signed_owner_mode"]["source_sha256"]) == 64
    assert len(data["m005_anchor"]["source_revision"]) == 40
    assert diagnose_review_gap(**data)["source_revision_mapping_verified"] is False


def test_forged_positive_review_objects_still_return_hold():
    # The crosswalk itself does NOT cryptographically verify either object.
    # It must never turn caller-asserted success into native execution.
    forged = fixture()
    forged["r14_anchor"]["mac"] = "f" * 64
    assert diagnose_review_gap(**forged)["status"] == "HOLD_INCOMPATIBLE_TRUST_DOMAINS"


@pytest.mark.parametrize("case", [
    "r14_missing", "r14_bad_schema", "r14_bad_status", "r14_global_true",
    "r14_dispatch_true", "r14_external_true", "r14_hostlocal_false",
    "r14_fidelity_true", "anchor_extra", "anchor_missing",
    "anchor_bad_schema", "anchor_audience", "anchor_bad_mac",
    "anchor_bad_event_hash", "anchor_no_registry_schema", "anchor_self_sign",
    "anchor_bool_sequence", "policy_schema", "policy_mode",
    "policy_scope", "policy_source", "policy_epoch_numeric",
    "m005_review_status", "m005_dispatch_true", "m005_worker_true",
    "m005_external_true", "m005_receipt_true", "m005_no_checkpoint",
    "m005_wrong_checkpoint", "m005_wrong_anchor_schema",
    "m005_wrong_phase", "m005_git_sha_wrong_length", "m005_corpus_sha_bad",
    "m005_epoch_bool", "m005_epoch_mismatch",
    "m005_revision_mismatch", "m005_sequence_zero", "r14_not_dict",
])
def test_fail_closed_on_malformed_or_claimed_authority(case):
    data = deepcopy(fixture())
    d = data["r14_decision"]
    a = data["r14_anchor"]
    p = data["r14_signed_owner_mode"]
    m = data["m005_result"]
    e = data["m005_anchor"]
    if case == "r14_missing":
        d.pop("schema")
    elif case == "r14_bad_schema":
        d["schema"] = "other"
    elif case == "r14_bad_status":
        d["status"] = "EXTERNAL_ANCHOR_OR_SQLITE_ROLLBACK_HOLD"
    elif case == "r14_global_true":
        d["global_consensus_proven"] = True
    elif case == "r14_dispatch_true":
        d["native_worker_job_dispatched"] = True
    elif case == "r14_external_true":
        d["real_external_anchor_authority_installed"] = True
    elif case == "r14_hostlocal_false":
        d["host_local_only"] = False
    elif case == "r14_fidelity_true":
        d["original_gameplay_fidelity_verified"] = True
    elif case == "anchor_extra":
        a["is_production_ready"] = True
    elif case == "anchor_missing":
        a.pop("mac")
    elif case == "anchor_bad_schema":
        a["schema"] = "OtherAnchor"
    elif case == "anchor_audience":
        a["audience"] = "ORCH-K003-execution"
    elif case == "anchor_bad_mac":
        a["mac"] = "invalid"
    elif case == "anchor_bad_event_hash":
        a["last_registry_event_sha256"] = "wrong"
    elif case == "anchor_no_registry_schema":
        a["source_registry_schema"] = "unknown"
    elif case == "anchor_self_sign":
        a["signer_id"] = a["source_producer_id"]
    elif case == "anchor_bool_sequence":
        a["external_anchor_sequence"] = True
    elif case == "policy_schema":
        p["schema"] = "OtherModeRecord"
    elif case == "policy_mode":
        p["mode"] = "BOTH_V1_V2"
    elif case == "policy_scope":
        p["owner_work_scope_sha256"] = "c" * 40
    elif case == "policy_source":
        p["source_sha256"] = "d" * 40
    elif case == "policy_epoch_numeric":
        p["owner_epoch"] = 4
    elif case == "m005_review_status":
        m["status"] = "PASS"
    elif case == "m005_dispatch_true":
        m["dispatch_authorized"] = True
    elif case == "m005_worker_true":
        m["worker_execution_authorized"] = True
    elif case == "m005_external_true":
        m["current_external_high_water_verified"] = True
    elif case == "m005_receipt_true":
        m["independent_owner_cas_authenticity_verified"] = True
    elif case == "m005_no_checkpoint":
        m.pop("next_checkpoint_proposal_only")
    elif case == "m005_wrong_checkpoint":
        m["next_checkpoint_proposal_only"]["schema"] = "production-ready"
    elif case == "m005_wrong_anchor_schema":
        e["schema"] = "Other"
    elif case == "m005_wrong_phase":
        e["phase"] = "PREPARED"
    elif case == "m005_git_sha_wrong_length":
        e["source_revision"] = "a" * 64
    elif case == "m005_corpus_sha_bad":
        e["corpus_sha256"] = "x" * 64
    elif case == "m005_epoch_bool":
        e["owner_epoch"] = True
    elif case == "m005_epoch_mismatch":
        e["owner_epoch"] = 5
    elif case == "m005_revision_mismatch":
        e["store_revision"] = 4
    elif case == "m005_sequence_zero":
        e["sequence"] = 0
    else:
        data["r14_anchor"] = "not-an-object"
    with pytest.raises(ContractGapRejected):
        diagnose_review_gap(**data)
