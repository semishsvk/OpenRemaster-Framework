"""Wire schema shape is never cryptographic authority."""
import json
from pathlib import Path
from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator, FormatChecker
from openremaster.m009_external_current_head import FIELDS
from test_m009_external_current_head import fixture

def validator():
    s=json.loads((Path(__file__).resolve().parents[1]/"contracts/orch-m009/external-current-head-v1.schema.json").read_text())
    Draft202012Validator.check_schema(s)
    assert set(s["required"]) == FIELDS | {"signature_b64"}
    return Draft202012Validator(s, format_checker=FormatChecker())

def test_valid_shape():
    _, args=fixture()
    validator().validate(args["receipt"])

@pytest.mark.parametrize("field,value", [("sequence",True),("audience","Execute"),("challenge","x"),("expires_utc","2026-02-30T20:00:00Z"),("extra",False)])
def test_invalid_wire(field,value):
    _, args=fixture()
    r=deepcopy(args["receipt"]); r[field]=value
    assert list(validator().iter_errors(r))
