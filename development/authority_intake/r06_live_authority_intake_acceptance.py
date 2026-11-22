"""Read-only acceptance harness for the R06 live-authority intake validator.

The cases use only missing evidence, existing historical replay material and
the existing D7 development self-signed receipt.  No live authority evidence
is generated and no worker/dispatch path is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPORT_SCHEMA = "OpenRemaster.R06.LiveAuthorityIntakeAcceptanceReport.v1"


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_case(validator: Path, args: list[str]) -> tuple[int, dict[str, Any]]:
    process = subprocess.run(
        [sys.executable, str(validator), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError:
        payload = {"parse_error": process.stdout[-1000:], "stderr": process.stderr[-1000:]}
    return process.returncode, payload


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=root / "outputs" / "OpenRemaster-R06-live-authority-intake-acceptance-2026-10-25.json")
    args = parser.parse_args()

    validator = root / "work" / "r06_live_authority_intake_validator.py"
    contract = root / "outputs" / "OpenRemaster-R06-live-receipt-intake-contract-2026-10-24.json"
    packet = root / "outputs" / "OpenRemaster-R06-admission-packet-2026-10-24.json"
    host_fixture = root / "work" / "D6-20261024T201501Z-C518C5E5" / "studio" / "src" / "data" / "host-connector-evidence.json"
    dev_receipt = root / "work" / "R06-dev-self-signed" / "dev-admission-receipt.json"

    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="openremaster-r06-intake-") as temp_name:
        temp = Path(temp_name)

        code, payload = run_case(validator, [])
        cases.append({
            "name": "missing_external_evidence",
            "return_code": code,
            "expected": {"return_code": 0, "status": "WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE", "missing_count": 4},
            "observed": {"return_code": code, "status": payload.get("status"), "missing_count": len(payload.get("missing_external_evidence", []))},
            "pass": code == 0 and payload.get("status") == "WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE" and len(payload.get("missing_external_evidence", [])) == 4,
        })

        code, payload = run_case(
            validator,
            ["--host-health-receipt", str(host_fixture), "--k003-admission-receipt", str(dev_receipt)],
        )
        cases.append({
            "name": "replay_host_and_dev_self_signed_k003_rejected",
            "return_code": code,
            "expected": {"return_code": 1, "status": "HOLD_BEFORE_DISPATCH", "rejected": ["host_health_receipt", "k003_admission_receipt"]},
            "observed": {"return_code": code, "status": payload.get("status"), "rejected": payload.get("rejected_external_evidence")},
            "pass": code == 1 and payload.get("status") == "HOLD_BEFORE_DISPATCH" and set(payload.get("rejected_external_evidence", [])) == {"host_health_receipt", "k003_admission_receipt"},
        })

        tampered_packet = temp / "tampered-packet.json"
        packet_payload = load(packet)
        packet_payload["work_package_sha256"] = "0" * 64
        tampered_packet.write_text(json.dumps(packet_payload, indent=2) + "\n", encoding="utf-8")
        code, payload = run_case(validator, ["--packet", str(tampered_packet)])
        cases.append({
            "name": "canonical_packet_hash_mismatch_holds",
            "return_code": code,
            "expected": {"return_code": 1, "status": "HOLD_BEFORE_DISPATCH", "canonical_failure": "canonical:packet_hash_matches_contract"},
            "observed": {"return_code": code, "status": payload.get("status"), "failures": payload.get("failures", [])},
            "pass": code == 1 and payload.get("status") == "HOLD_BEFORE_DISPATCH" and "canonical:packet_hash_matches_contract" in payload.get("failures", []),
        })

        malformed = temp / "malformed-host.json"
        malformed.write_text("{not-json", encoding="utf-8")
        code, payload = run_case(validator, ["--host-health-receipt", str(malformed)])
        cases.append({
            "name": "malformed_external_artifact_rejected",
            "return_code": code,
            "expected": {"return_code": 1, "status": "HOLD_BEFORE_DISPATCH", "rejected": ["host_health_receipt"]},
            "observed": {"return_code": code, "status": payload.get("status"), "rejected": payload.get("rejected_external_evidence")},
            "pass": code == 1 and payload.get("status") == "HOLD_BEFORE_DISPATCH" and "host_health_receipt" in payload.get("rejected_external_evidence", []),
        })

        manifest_dir = temp / "manifest"
        manifest_dir.mkdir()
        shutil.copy2(host_fixture, manifest_dir / "host_health_receipt.json")
        manifest = {
            "schema": "OpenRemaster.R06.LiveAuthorityEvidenceManifest.v1",
            "operation_id": load(packet)["operation_id"],
            "work_package_sha256": load(packet)["work_package_sha256"],
            "artifacts": {
                "host_health_receipt": {"path": "host_health_receipt.json", "sha256": "0" * 64},
                "k003_admission_receipt": {"path": "k003_admission_receipt.json", "sha256": "0" * 64},
                "owner_receipt": {"path": "owner_receipt.json", "sha256": "0" * 64},
                "witness_receipt": {"path": "witness_receipt.json", "sha256": "0" * 64},
                "signature_verification_result": {"path": "signature_verification_result.json", "sha256": "0" * 64},
            },
        }
        manifest_path = manifest_dir / "live-evidence-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        code, payload = run_case(validator, ["--evidence-manifest", str(manifest_path)])
        cases.append({
            "name": "manifest_digest_mismatch_holds",
            "return_code": code,
            "expected": {"return_code": 1, "status": "HOLD_BEFORE_DISPATCH", "rejected": ["live_evidence_manifest"]},
            "observed": {"return_code": code, "status": payload.get("status"), "rejected": payload.get("rejected_external_evidence"), "failures": payload.get("failures", [])},
            "pass": code == 1 and payload.get("status") == "HOLD_BEFORE_DISPATCH" and "rejected:live_evidence_manifest" in payload.get("failures", []),
        })

    passed = sum(case["pass"] is True for case in cases)
    failed = len(cases) - passed
    report = {
        "schema": REPORT_SCHEMA,
        "validator": str(validator.resolve()),
        "validator_sha256": sha256(validator),
        "status": "PASS_READONLY_INTAKE_ACCEPTANCE" if failed == 0 else "FAIL_READONLY_INTAKE_ACCEPTANCE",
        "cases_passed": passed,
        "cases_failed": failed,
        "cases": cases,
        "authority_bound": False,
        "synthetic_live_evidence_created": False,
        "dispatch_authorized": False,
        "dispatch_performed": False,
        "worker_started_by_harness": False,
        "production_go": False,
        "scope": "negative and fail-closed intake tests only; no live authority or dispatch",
        "next_gate": "Use the validator with fresh external Host/K003/Owner/Witness/signature artifacts; keep consolidated R06 gate HOLD until independent evidence passes.",
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
