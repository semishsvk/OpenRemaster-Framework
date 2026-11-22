"""Execution-boundary admission verification for the DEV candidate.

The trust root is supplied by the control plane as ``trusted_keys``. A caller
cannot make its own public key trusted, replace the expected digest, or use a
development self-signed receipt. Verification must run immediately before a
worker spawn. This module only verifies; it does not start a process.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from typing import Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class AdmissionRejected(ValueError):
    """Fail-closed execution admission rejection."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def verify_before_spawn(envelope: Mapping[str, object], request: Mapping[str, object], trusted_keys: Mapping[str, bytes], *, now: float | None = None) -> dict[str, object]:
    required = {"schema", "operation_id", "request_sha256", "project_id", "capability", "nonce", "fence", "issuer_kid", "not_after", "signature_b64"}
    if set(envelope) != required or envelope.get("schema") != "OpenRemaster.ExecutionAdmission.v1":
        raise AdmissionRejected("ENVELOPE_SCHEMA")
    if envelope.get("request_sha256") != _digest(dict(request)):
        raise AdmissionRejected("REQUEST_DIGEST_MISMATCH")
    if not isinstance(envelope.get("operation_id"), str) or not re.fullmatch(r"[a-f0-9]{32}", envelope["operation_id"]):
        raise AdmissionRejected("OPERATION_ID")
    if not isinstance(envelope.get("nonce"), str) or not envelope["nonce"] or len(envelope["nonce"]) > 256:
        raise AdmissionRejected("NONCE")
    if type(envelope.get("fence")) is not int or envelope["fence"] < 1:
        raise AdmissionRejected("FENCE")
    kid = envelope["issuer_kid"]
    if not isinstance(kid, str) or kid not in trusted_keys:
        raise AdmissionRejected("ISSUER_NOT_TRUSTED")
    if type(envelope.get("not_after")) not in (int, float) or float(envelope["not_after"]) <= (time.time() if now is None else now):
        raise AdmissionRejected("EXPIRED")
    try:
        public = Ed25519PublicKey.from_public_bytes(trusted_keys[kid])
        signed = {key: envelope[key] for key in required if key != "signature_b64"}
        public.verify(base64.b64decode(envelope["signature_b64"], validate=True), canonical(signed))
    except Exception as exc:
        raise AdmissionRejected("SIGNATURE") from exc
    return {"status": "ADMISSION_VERIFIED_BEFORE_SPAWN", "operation_id": envelope["operation_id"], "issuer_kid": kid, "fence": envelope["fence"], "production_go": False, "dispatch_authorized": False}
