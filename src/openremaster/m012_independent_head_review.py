"""M012 independent current-head comparison: review only, no native authority.

Both receipts must be independently signed by different pinned test authorities.
The caller-supplied trust views cannot establish globally CURRENT state.
"""
from __future__ import annotations
from hashlib import sha256
from openremaster.m011_signed_recovery import (
    SignedRecoveryHold, verify_signed_recovery_receipt,
)

class IndependentHeadHold(ValueError):
    pass

def compare_signed_independent_heads(*, recovery_receipt, recovery_trust,
    witness_receipt, witness_trust, recovery_authority, witness_authority, now):
    if recovery_authority == witness_authority:
        raise IndependentHeadHold("witness cannot be the recovery signer")
    try:
        a=verify_signed_recovery_receipt(receipt=recovery_receipt,
            trust=recovery_trust,expected_authority=recovery_authority,now=now)
        b=verify_signed_recovery_receipt(receipt=witness_receipt,
            trust=witness_trust,expected_authority=witness_authority,now=now)
    except SignedRecoveryHold as exc:
        raise IndependentHeadHold("invalid signed input") from exc
    x=a["verified_receipt_copy"]
    y=b["verified_receipt_copy"]
    fields=("scope","operation_id","probe_id","challenge","request_sha256",
            "prior_head_sha256","candidate_head_sha256","remote_head_sha256",
            "sequence","owner_epoch","fence_generation","result",
            "remote_operation_sha256","m009_head_receipt_sha256")
    if any(x[k]!=y[k] for k in fields):
        raise IndependentHeadHold("signed independent witness mismatch")
    if (set(recovery_trust.public_keys.values()) & set(witness_trust.public_keys.values())):
        raise IndependentHeadHold("shared signing key material across authorities")
    return {
        "status":"TWO_SIGNED_CLAIMS_MATCH_REVIEW_ONLY",
        "recovery_receipt_sha256":a["receipt_sha256"],
        "witness_receipt_sha256":b["receipt_sha256"],
        "two_distinct_signatures_verified":True,
        "independent_live_current_head_verified":False,
        "remote_nonce_consumed_verified":False,
        "global_cas_authorized":False,
        "native_worker_dispatch_authorized":False,
    }
