"""ORCH-M006: source-contract *gap* inspection. NEVER authorization.

Review-only structural crosswalk between R14 host-local HMAC evidence and
M005 Ed25519 candidate evidence. Does not verify signatures, query a trusted
external high-water, acquire leases, launch jobs, or read a production store.
Any apparently positive inputs remain NON-AUTHORIZING.
"""
from __future__ import annotations

import re

R14_DECISION = "OpenRemaster.R14RegistryExternalAnchorDecision.v1"
R14_ANCHOR = "OpenRemaster.R14IndependentRegistryAnchor.v1"
R14_POLICY = "OpenRemaster.R13SignedOwnerModeDecision.v1"
M005_ANCHOR = "ORCH-M005.SignedAnchor.v0"
M005_REVIEW = "SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF"
R14_REVIEW = "SIGNED_HOSTLOCAL_REGISTRY_MATCHES_EXTERNAL_REVIEW_ANCHOR"
M006_SCHEMA = "ORCH-M006.R14M005ContractGap.v0"

R14_FIELDS = frozenset({
    "schema", "audience", "registry_id", "external_anchor_sequence",
    "prior_external_anchor_sha256", "registry_event_count",
    "registry_mode_count", "last_registry_event_sha256",
    "source_registry_schema", "captured_at_unix", "expires_at_unix",
    "signer_id", "source_producer_id", "mac",
})
GAPS = (
    "R14_EVENT_HASH_NOT_M005_OWNER_RECEIPT_CHAIN",
    "R14_HMAC_AUDIENCE_NOT_M005_ED25519_SIGNED_DOMAIN",
    "R14_OWNER_EPOCH_IDENTIFIER_NOT_M005_MONOTONIC_EPOCH",
    "R14_OWNER_SCOPE_NOT_BOUND_TO_M005_NAMESPACE",
    "R14_SOURCE_SHA256_NOT_M005_GIT_REVISION",
    "R14_HOSTLOCAL_OBSERVATION_NOT_REMOTE_CURRENT_HIGHWATER",
    "M005_LAB_RECEIPT_NOT_INDEPENDENT_NATIVE_OWNER_CAS",
    "GLOBAL_NONCE_CAS_AND_WORKER_SIDE_FENCE_NOT_INSTALLED",
)
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
NAME = re.compile(r"[A-Za-z0-9_.-]{3,128}\Z")


class ContractGapRejected(ValueError):
    """Unexpected or potentially authority-confusing review input."""


def _dict(value, label):
    if type(value) is not dict:
        raise ContractGapRejected(f"{label} must be object")
    return value


def _false(data, name, label):
    if data.get(name) is not False:
        raise ContractGapRejected(f"{label}.{name} must be strictly false")


def _string(data, field, pattern, label):
    value = data.get(field)
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise ContractGapRejected(f"{label}.{field} invalid")
    return value


def _counter(data, field, minimum=0):
    value = data.get(field)
    if type(value) is not int or value < minimum:
        raise ContractGapRejected(f"{field} must be integer >= {minimum}")
    return value


def diagnose_review_gap(*, r14_decision, r14_anchor,
                        r14_signed_owner_mode, m005_result, m005_anchor):
    """Return an explicit HOLD after *structural* cross-domain review.

    Never convert an R14 HMAC anchor into an Ed25519 signature or treat
    a positive result from either prototype as native owner admission.
    Callers must independently run the original verifiers; this helper
    deliberately cannot attest that they did so.
    """
    r14 = _dict(r14_decision, "r14_decision")
    a14 = _dict(r14_anchor, "r14_anchor")
    policy = _dict(r14_signed_owner_mode, "r14_signed_owner_mode")
    m005 = _dict(m005_result, "m005_result")
    a5 = _dict(m005_anchor, "m005_anchor")
    if r14.get("schema") != R14_DECISION or r14.get("status") != R14_REVIEW:
        raise ContractGapRejected("R14 original verifier review result absent")
    if r14.get("host_local_only") is not True:
        raise ContractGapRejected("R14 origin not identified as host-local")
    for field in ("real_external_anchor_authority_installed",
                  "global_consensus_proven", "native_worker_job_dispatched",
                  "original_gameplay_fidelity_verified"):
        _false(r14, field, "r14_decision")
    if set(a14) != R14_FIELDS or a14.get("schema") != R14_ANCHOR:
        raise ContractGapRejected("R14 anchor fields/version differ")
    if a14["audience"] != "ORF-ExternalRegistryAnchor-OwnerReviewOnly-v1":
        raise ContractGapRejected("R14 signing audience not review-only")
    for field in ("prior_external_anchor_sha256",
                  "last_registry_event_sha256", "mac"):
        _string(a14, field, HEX64, "r14_anchor")
    for field in ("external_anchor_sequence", "registry_event_count",
                  "registry_mode_count"):
        _counter(a14, field, 1 if field == "external_anchor_sequence" else 0)
    if a14.get("source_registry_schema") != "OpenRemaster.R13HostLocalExclusiveOwnerRegistry.v1":
        raise ContractGapRejected("R14 source registry protocol differs")
    if a14.get("signer_id") == a14.get("source_producer_id"):
        raise ContractGapRejected("R14 self-signer is invalid")
    if policy.get("schema") != R14_POLICY or policy.get("mode") not in (
        "LEGACY_V1_ALLOWED", "V2_REQUIRED"
    ):
        raise ContractGapRejected("R14 signed owner mode protocol differs")
    _string(policy, "owner_work_scope_sha256", HEX64, "r14_policy")
    _string(policy, "source_sha256", HEX64, "r14_policy")
    _string(policy, "owner_epoch", NAME, "r14_policy")
    if m005.get("status") != M005_REVIEW:
        raise ContractGapRejected("M005 signed-candidate review result absent")
    for field in ("dispatch_authorized", "worker_execution_authorized",
                  "current_external_high_water_verified",
                  "independent_owner_cas_authenticity_verified"):
        _false(m005, field, "m005_result")
    proposed = _dict(m005.get("next_checkpoint_proposal_only"), "M005 proposed checkpoint")
    if proposed.get("schema") != "ORCH-M005.PinnedHighWater.v0":
        raise ContractGapRejected("M005 proposal is not a review-only checkpoint")
    if a5.get("schema") != M005_ANCHOR or a5.get("phase") != "COMMITTED":
        raise ContractGapRejected("M005 signed anchor protocol differs")
    _string(a5, "source_revision", HEX40, "m005_anchor")
    _string(a5, "corpus_sha256", HEX64, "m005_anchor")
    _counter(a5, "owner_epoch", 1)
    _counter(a5, "store_revision", 1)
    _counter(a5, "sequence", 1)
    if proposed.get("owner_epoch") != a5["owner_epoch"] or (
        proposed.get("store_revision") != a5["store_revision"]
    ):
        raise ContractGapRejected("M005 internal counters disagree")

    return {
        "schema": M006_SCHEMA,
        "status": "HOLD_INCOMPATIBLE_TRUST_DOMAINS",
        "review_evidence_seen_not_authenticated_by_crosswalk": True,
        "global_owner_authority_verified": False,
        "current_external_high_water_verified": False,
        "r14_m005_epoch_mapping_verified": False,
        "owner_work_scope_binding_verified": False,
        "source_revision_mapping_verified": False,
        "native_cas_receipt_provenance_verified": False,
        "worker_side_fencing_verified": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
        "gaps": list(GAPS),
        "r14_source_mode": policy["mode"],
        "r14_anchor_event_count": a14["registry_event_count"],
        "m005_candidate_sequence": a5["sequence"],
        "note": "Both source domains are REVIEW ONLY; no semantic/cryptographic adapter installed.",
    }
