"""M008 Draft2020-12 wire schemas: shape validation is NOT cryptographic trust."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from openremaster.m008_owner_observation_attestation import (
    ATTEST_FIELDS, HIGHWATER_FIELDS,
)
from test_m008_owner_observation_attestation import sample

ROOT = Path(__file__).resolve().parents[1] / "contracts" / "orch-m008"


def schema(name):
    data = json.loads((ROOT / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(data)
    return data


def validator(name):
    checker = FormatChecker()
    if "date-time" not in checker.checkers:
        raise RuntimeError("RFC3339 optional date-time checker missing: rfc3339-validator required")
    return Draft202012Validator(schema(name), format_checker=checker)


def test_attestation_schema_matches_python_contract_exactly():
    s = schema("owner-observation-attestation-v1.schema.json")
    assert set(s["properties"]) == set(s["required"]) == ATTEST_FIELDS
    assert s["additionalProperties"] is False


def test_highwater_schema_matches_python_contract_exactly():
    s = schema("pinned-owner-highwater-v1.schema.json")
    assert set(s["properties"]) == set(s["required"]) == HIGHWATER_FIELDS
    assert s["additionalProperties"] is False


def test_test_signed_attestation_validates_as_wire_shape_only():
    key, bundle = sample()
    v = validator("owner-observation-attestation-v1.schema.json")
    assert list(v.iter_errors(bundle["attestation"])) == []
    assert list(validator("pinned-owner-highwater-v1.schema.json").iter_errors(bundle["independently_pinned_highwater"])) == []


@pytest.mark.parametrize("change", [
    "missing-field", "extra-field", "wrong-version", "wrong-audience",
    "bad-observed-date", "timezone-not-z", "bad-sha256",
    "bad-git-sha", "bool-owner-epoch", "negative-fence",
    "wrong-challenge", "invalid-base64-character", "zero-owner-epoch",
])
def test_invalid_attestation_wire_shape_rejected(change):
    key, bundle = sample()
    a = deepcopy(bundle["attestation"])
    if change == "missing-field":
        a.pop("source_capture_sha256")
    elif change == "extra-field":
        a["dispatch_authorized"] = True
    elif change == "wrong-version":
        a["schema"] = "ORF-M008.PRODUCTION_AUTHORIZED"
    elif change == "wrong-audience":
        a["audience"] = "ORF-NativeK003-Execute"
    elif change == "bad-observed-date":
        a["observed_utc"] = "2026-02-30T20:00:18Z"
    elif change == "timezone-not-z":
        a["observed_utc"] = "2026-10-13T22:00:18+02:00"
    elif change == "bad-sha256":
        a["source_capture_sha256"] = "notsha"
    elif change == "bad-git-sha":
        a["m005_source_revision"] = "a" * 64
    elif change == "bool-owner-epoch":
        a["owner_epoch_counter"] = True
    elif change == "negative-fence":
        a["fence_generation"] = -1
    elif change == "wrong-challenge":
        a["challenge"] = "../bad"
    elif change == "invalid-base64-character":
        a["signature_b64"] = "!!"
    else:
        a["owner_epoch_counter"] = 0
    assert list(validator("owner-observation-attestation-v1.schema.json").iter_errors(a))


@pytest.mark.parametrize("change", [
    "bad-schema", "unknown-extra", "missing", "negative-sequence",
    "boolean-sequence", "bad-head-hash", "wrong-authority",
])
def test_invalid_highwater_wire_shape_rejected(change):
    _, bundle = sample()
    h = deepcopy(bundle["independently_pinned_highwater"])
    if change == "bad-schema":
        h["schema"] = "PRODUCTION_CURRENT_HEAD"
    elif change == "unknown-extra":
        h["signed_witness_approved"] = True
    elif change == "missing":
        h.pop("last_attestation_sha256")
    elif change == "negative-sequence":
        h["sequence"] = -1
    elif change == "boolean-sequence":
        h["sequence"] = True
    elif change == "bad-head-hash":
        h["last_attestation_sha256"] = "wrong"
    else:
        h["authority_id"] = "evil authority"
    assert list(validator("pinned-owner-highwater-v1.schema.json").iter_errors(h))


def test_schema_positive_never_implies_signature_or_current_owner_proof():
    _, bundle = sample()
    a = deepcopy(bundle["attestation"])
    a["signature_b64"] = "A" * 86 + "=="
    # This is a syntactically valid 64-byte-size base64, not a valid Ed25519 signature.
    assert list(validator("owner-observation-attestation-v1.schema.json").iter_errors(a)) == []
    assert a["schema"] == "ORF-M008.OwnerObservationAttestation.v1"
    assert "dispatch_authorized" not in a
    # The actual runtime verifier MUST perform Ed25519 and scope checks separately.
