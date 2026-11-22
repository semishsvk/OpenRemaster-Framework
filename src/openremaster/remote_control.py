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
