"""Ephemeral development-only self-signed receipt issuer.

The Ed25519 private key is generated in memory for one receipt and is never
written to disk. This issuer cannot create live K003 authority or production
dispatch evidence.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def load(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("issue", choices=["issue"])
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--operation-id", required=True)
    parser.add_argument("--packet-out", required=True, type=Path)
    parser.add_argument("--receipt-out", required=True, type=Path)
    args = parser.parse_args()

    if not re.fullmatch(r"[a-f0-9]{32}", args.operation_id):
        raise SystemExit("OPERATION_ID_DENIED")
    packet = load(args.template)
    packet["operation_id"] = args.operation_id
    packet["dispatch_authorized"] = False
    packet["production_go"] = False
    packet["status"] = "PREPARED_NOT_DISPATCHED"
    args.packet_out.parent.mkdir(parents=True, exist_ok=True)
    args.packet_out.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")

    packet_payload = {
        "operation_id": packet["operation_id"],
        "work_package_sha256": packet["work_package_sha256"],
        "project_id": packet["work_package"]["project_id"],
        "capability": packet["work_package"]["capability"],
    }
    payload = canonical(packet_payload)
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes_raw()
    receipt = {
        "schema": "OpenRemaster.K003.DevSelfSignedReceipt.v1",
        "development_only": True,
        "self_signed": True,
        "authority_scope": "DEV_SELF_SIGNED",
        "live_receipt": False,
        **packet_payload,
        "decision": "ADMIT_DEV_ONLY",
        "authority_authenticated": False,
        "owner_admitted": False,
        "witness_admitted": False,
        "dev_fence_verified": True,
        "production_go": False,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "public_key_b64": base64.b64encode(public_key).decode("ascii"),
        "signature_b64": base64.b64encode(key.sign(payload)).decode("ascii"),
    }
    args.receipt_out.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_out.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "DEV_EPHEMERAL_SELF_SIGNED_CREATED",
        "authority_bound": False,
        "dispatch_authorized": False,
        "production_go": False,
        "private_key_persisted": False,
        "operation_id": args.operation_id,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
