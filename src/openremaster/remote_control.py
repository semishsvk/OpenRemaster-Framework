"""M001 pure contract checks; no transport, credentials, or job execution."""
import hashlib
import json
from datetime import datetime, timezone


def canonical_digest(document):
    """SHA-256 of UTF-8 JSON, sorted keys, compact separators, no NaN."""
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_binding(request, worker, receipt, *, now):
    """Call after JSON Schema validation. Raise on an unsafe binding.

    Readiness is advisory, never authorization. Authentication and durable
    idempotency must be implemented by a future transport before dispatch.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone aware")
    deadline = datetime.fromisoformat(request["deadline_utc"].replace("Z", "+00:00"))
    observed = datetime.fromisoformat(worker["observed_utc"].replace("Z", "+00:00"))
    age = (now - observed).total_seconds()
    if deadline <= now or not 0 <= age <= 60:
        raise ValueError("expired request or stale/future worker status")
    if worker["state"] != "READY" or request["operation"] not in worker["capabilities"]:
        raise ValueError("worker unavailable or unsupported")
    expected = (request["request_id"], request["worker_id"],
                canonical_digest(request), request["revision"])
    actual = (receipt["request_id"], receipt["worker_id"],
              receipt["request_sha256"], receipt["revision"])
    if request["worker_id"] != worker["worker_id"] or expected != actual:
        raise ValueError("request/worker/receipt binding mismatch")
    return receipt["status"]


def validate_bundle(request, worker, receipt, *, now, schema_directory):
    """Validate trusted v1 schemas, then bind the three untrusted documents.

    schema_directory must be the contracts/remote-control/v1 directory from
    a caller-pinned trusted checkout, never a path from an incoming message.
    The returned status is structural only and grants no execution authority.
    Dependencies are loaded lazily so legacy digest-only users are unaffected.
    """
    from pathlib import Path
    from jsonschema import Draft202012Validator, FormatChecker

    checker = FormatChecker()
    if "date-time" not in checker.checkers:
        raise RuntimeError("RFC 3339 date-time checker unavailable; install rfc3339-validator==0.1.4")
    validators = []
    for name in ("request", "worker-status", "receipt"):
        path = Path(schema_directory) / (name + ".schema.json")
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validators.append(Draft202012Validator(schema, format_checker=checker))
    for validator, document in zip(validators, (request, worker, receipt)):
        validator.validate(document)
    return check_binding(request, worker, receipt, now=now)
