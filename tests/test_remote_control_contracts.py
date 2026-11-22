"""Synthetic M001 checks. No network, worker, corpus, or subprocess."""
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from openremaster.remote_control import canonical_digest, check_binding

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def document(name):
    return json.loads((ROOT / "tests/fixtures/remote-control/v1" / (name + ".json")).read_text())


def validator(name):
    schema = json.loads((ROOT / "contracts/remote-control/v1" / (name + ".schema.json")).read_text())
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()
    if "date-time" not in checker.checkers:
        raise RuntimeError("RFC 3339 date-time checker unavailable; install rfc3339-validator==0.1.4")
    return Draft202012Validator(schema, format_checker=checker)


def bundle():
    request, worker = document("request"), document("worker-status")
    receipt = dict(schema_version="1.0", request_id=request["request_id"],
                   worker_id=request["worker_id"], request_sha256=canonical_digest(request),
                   revision=request["revision"], status="PASS",
                   evidence_sha256="c" * 64, error_code=None)
    return request, worker, receipt


def test_valid_round_trip():
    request, worker, receipt = bundle()
    for name, value in zip(("request", "worker-status", "receipt"), (request, worker, receipt)):
        validator(name).validate(value)
        assert json.loads(json.dumps(value)) == value
    assert check_binding(request, worker, receipt, now=NOW) == "PASS"


@pytest.mark.parametrize("name,field,value", [
    ("request", "schema_version", "2.0"),
    ("request", "operation", "shell.exec"),
    ("request", "revision", "main"),
    ("request", "input_sha256", "unknown"),
    ("request", "deadline_utc", "tomorrow"),
    ("request", "deadline_utc", "2030-01-01T00:00:00"),
    ("request", "source_url", "https://example.invalid/token"),
    ("request", "limits", {"timeout_seconds": 61, "max_output_bytes": 1}),
    ("request", "limits", {"timeout_seconds": True, "max_output_bytes": 1}),
    ("worker-status", "state", "VERIFIED"),
    ("worker-status", "capabilities", []),
    ("receipt", "evidence_sha256", None),
    ("receipt", "error_code", "VALIDATION_FAILED"),
])
def test_reject_invalid_contract(name, field, value):
    values = dict(zip(("request", "worker-status", "receipt"), bundle()))
    bad = copy.deepcopy(values[name])
    bad[field] = value
    assert list(validator(name).iter_errors(bad))


@pytest.mark.parametrize("name", ["request", "worker-status", "receipt"])
def test_all_fields_required(name):
    value = dict(zip(("request", "worker-status", "receipt"), bundle()))[name]
    for field in value:
        bad = dict(value)
        del bad[field]
        assert list(validator(name).iter_errors(bad)), field


@pytest.mark.parametrize("field", ["request_id", "worker_id", "request_sha256", "revision"])
def test_reject_receipt_binding_mismatch(field):
    request, worker, receipt = bundle()
    receipt[field] = "d" * (64 if field == "request_sha256" else 40)
    with pytest.raises(ValueError):
        check_binding(request, worker, receipt, now=NOW)


@pytest.mark.parametrize("state", ["UNKNOWN", "OFFLINE", "BUSY"])
def test_unavailable_worker(state):
    request, worker, receipt = bundle()
    worker["state"] = state
    with pytest.raises(ValueError):
        check_binding(request, worker, receipt, now=NOW)


@pytest.mark.parametrize("observed", ["2026-10-13T11:58:59Z", "2026-10-13T12:00:01Z"])
def test_stale_or_future_worker(observed):
    request, worker, receipt = bundle()
    worker["observed_utc"] = observed
    with pytest.raises(ValueError):
        check_binding(request, worker, receipt, now=NOW)


def test_expiry_boundary():
    request, worker, receipt = bundle()
    request["deadline_utc"] = NOW.isoformat()
    receipt["request_sha256"] = canonical_digest(request)
    with pytest.raises(ValueError):
        check_binding(request, worker, receipt, now=NOW)


def test_unknown_is_not_pass():
    request, worker, receipt = bundle()
    receipt.update(status="UNKNOWN", evidence_sha256=None)
    validator("receipt").validate(receipt)
    assert check_binding(request, worker, receipt, now=NOW) == "UNKNOWN"


def test_canonical_identity():
    request = document("request")
    assert canonical_digest(request) == canonical_digest(dict(reversed(list(request.items()))))
    changed = copy.deepcopy(request)
    changed["limits"]["timeout_seconds"] += 1
    assert canonical_digest(request) != canonical_digest(changed)
    with pytest.raises(ValueError):
        canonical_digest({"value": float("nan")})


def test_missing_date_time_checker_fails_closed(monkeypatch):
    class MissingDateTimeChecker:
        checkers = {}

    monkeypatch.setitem(globals(), "FormatChecker", MissingDateTimeChecker)
    with pytest.raises(RuntimeError, match="rfc3339-validator"):
        validator("request")
