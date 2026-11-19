"""M011 signed receipt wire schema is structural ONLY, not cryptographic trust."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from openremaster.m011_signed_recovery import (
    SIGNED_FIELDS, SignedRecoveryHold, verify_signed_recovery_receipt,
)
from test_m011_signed_recovery import make_receipt, private_and_trust, NOW, REGISTRY

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "contracts" / "orch-m011" / "signed-remote-recovery-v1.schema.json"


def contract():
    data = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(data)
    return data


def validator():
    checker = FormatChecker()
    if "date-time" not in checker.checkers:
        raise RuntimeError("RFC3339 format validator not installed; fail closed")
    return Draft202012Validator(contract(), format_checker=checker)


def test_exact_json_schema_matches_signed_runtime_contract():
    c = contract()
    assert set(c["properties"]) == set(c["required"]) == SIGNED_FIELDS
    assert c["additionalProperties"] is False


def test_ephemeral_key_signed_receipt_passes_wire_structure_and_ed25519_only():
    key, trust = private_and_trust()
    row = make_receipt(key)
    assert list(validator().iter_errors(row)) == []
    assert verify_signed_recovery_receipt(
        receipt=row, trust=trust, expected_authority=REGISTRY,
        now=NOW,
    )["external_current_head_verified"] is False


@pytest.mark.parametrize("change", [
    "unknown-field", "missing-field", "wrong-schema",
    "wrong-audience", "bad-result", "unknown-remote-result",
    "bad-sha256", "uppercase-hash", "wrong-owner-sequence",
    "boolean-epoch", "negative-fence", "zero-trust-generation",
    "bad-challenge", "wrong-signature-shape",
    "noncanonical-padded-signature", "offset-date", "invalid-calendar",
    "empty-authority",
])
def test_invalid_wire_shape_rejected(change):
    key, _ = private_and_trust()
    data = deepcopy(make_receipt(key))
    if change == "unknown-field":
        data["native_dispatch_authorized"] = True
    elif change == "missing-field":
        data.pop("m009_head_receipt_sha256")
    elif change == "wrong-schema":
        data["schema"] = "M011.PRODUCTION_READY"
    elif change == "wrong-audience":
        data["audience"] = "ORF-NATIVE-WORKER-EXECUTE"
    elif change == "bad-result":
        data["result"] = "PASS"
    elif change == "unknown-remote-result":
        data["result"] = "UNKNOWN"
    elif change == "bad-sha256":
        data["remote_operation_sha256"] = "invalid"
    elif change == "uppercase-hash":
        data["candidate_head_sha256"] = "A" * 64
    elif change == "wrong-owner-sequence":
        data["sequence"] = 0
    elif change == "boolean-epoch":
        data["owner_epoch"] = True
    elif change == "negative-fence":
        data["fence_generation"] = -1
    elif change == "zero-trust-generation":
        data["trust_generation"] = 0
    elif change == "bad-challenge":
        data["challenge"] = "../escape"
    elif change == "wrong-signature-shape":
        data["signature_b64"] = "bad"
    elif change == "noncanonical-padded-signature":
        data["signature_b64"] += "=="
    elif change == "offset-date":
        data["expires_utc"] = "2026-10-14T15:00:35+02:00"
    elif change == "invalid-calendar":
        data["issued_utc"] = "2026-02-30T13:00:00Z"
    else:
        data["authority_id"] = ""
    assert list(validator().iter_errors(data))


def test_valid_wire_shape_with_forged_signature_is_still_untrusted():
    key, trust = private_and_trust()
    data = make_receipt(key)
    data["signature_b64"] = "A" * 86 + "=="
    assert list(validator().iter_errors(data)) == []
    with pytest.raises(SignedRecoveryHold, match="signature invalid"):
        verify_signed_recovery_receipt(
            receipt=data, trust=trust, expected_authority=REGISTRY,
            now=NOW,
        )


def test_wire_schema_cannot_prove_remote_challenge_consumption():
    key, trust = private_and_trust()
    data = make_receipt(key)
    assert list(validator().iter_errors(data)) == []
    assert "dispatch_authorized" not in data
    decision = verify_signed_recovery_receipt(
        receipt=data, trust=trust, expected_authority=REGISTRY, now=NOW
    )
    assert decision["remote_nonce_consumption_verified"] is False
    assert decision["native_worker_dispatch_authorized"] is False
