"""Development-only Ed25519 self-signed receipt generator/verifier.

This module deliberately cannot produce a live K003 receipt or authorize
dispatch. It signs only a local packet binding and marks the result DEV_ONLY.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def load(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sign = sub.add_parser("sign")
    sign.add_argument("--packet", required=True, type=Path)
    sign.add_argument("--private-key", required=True, type=Path)
    sign.add_argument("--output", required=True, type=Path)
    verify = sub.add_parser("verify")
    verify.add_argument("--packet", required=True, type=Path)
    verify.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    packet = load(args.packet)
    packet_payload = {
        "operation_id": packet["operation_id"],
        "work_package_sha256": packet["work_package_sha256"],
        "project_id": packet["work_package"]["project_id"],
        "capability": packet["work_package"]["capability"],
    }
    payload = canonical(packet_payload)
    payload_hash = hashlib.sha256(payload).hexdigest()

    if args.command == "sign":
        private_raw = base64.b64decode(args.private_key.read_text(encoding="ascii").strip())
        private_key = Ed25519PrivateKey.from_private_bytes(private_raw)
        public_key = private_key.public_key().public_bytes_raw()
        receipt = {
            "schema": "OpenRemaster.K003.DevSelfSignedReceipt.v1",
            "development_only": True,
            "self_signed": True,
            "authority_scope": "DEV_SELF_SIGNED",
            "live_receipt": False,
            "operation_id": packet_payload["operation_id"],
            "work_package_sha256": packet_payload["work_package_sha256"],
            "project_id": packet_payload["project_id"],
            "capability": packet_payload["capability"],
            "decision": "ADMIT_DEV_ONLY",
            "authority_authenticated": False,
            "owner_admitted": False,
            "witness_admitted": False,
            "dev_fence_verified": True,
            "production_go": False,
            "payload_sha256": payload_hash,
            "public_key_b64": base64.b64encode(public_key).decode("ascii"),
            "signature_b64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
        }
        args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "DEV_SELF_SIGNED_CREATED", "authority_bound": False, "dispatch_authorized": False, "output": str(args.output.resolve())}, indent=2))
        return 0

    receipt = load(args.receipt)
    failures: list[str] = []
    if receipt.get("schema") != "OpenRemaster.K003.DevSelfSignedReceipt.v1":
        failures.append("schema")
    if receipt.get("development_only") is not True or receipt.get("self_signed") is not True:
        failures.append("dev_markers")
    if receipt.get("authority_scope") != "DEV_SELF_SIGNED" or receipt.get("live_receipt") is not False:
        failures.append("authority_scope")
    for key in ("operation_id", "work_package_sha256", "project_id", "capability"):
        if receipt.get(key) != packet_payload[key]:
            failures.append(f"binding:{key}")
    if receipt.get("production_go") is not False or receipt.get("authority_authenticated") is not False or receipt.get("owner_admitted") is not False or receipt.get("witness_admitted") is not False:
        failures.append("production_or_authority_flags")
    if receipt.get("payload_sha256") != payload_hash:
        failures.append("payload_hash")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(receipt["public_key_b64"]))
        public_key.verify(base64.b64decode(receipt["signature_b64"]), payload)
    except Exception:
        failures.append("signature")
    result = {
        "schema": "OpenRemaster.R06.DevSelfSignedVerificationResult.v1",
        "status": "DEV_SELF_SIGNED_VALID" if not failures else "FAIL_DEV_SELF_SIGNED",
        "failures": failures,
        "authority_bound": False,
        "dispatch_authorized": False,
        "production_go": False,
        "scope": "development-only integrity verification; not live K003 authority",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
