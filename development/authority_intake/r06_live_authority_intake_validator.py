"""Read-only intake validator for future external R06 authority evidence.

The validator consumes evidence supplied by an external authority handoff and
checks only schema, freshness, binding and explicit admission markers.  It
never creates a receipt, performs cryptographic verification, starts a worker,
dispatches an operation or changes any supplied evidence file.

The validator is deliberately conservative: absent evidence is reported as
WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE and malformed, historical, fixture or
unbound evidence remains HOLD_BEFORE_DISPATCH.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


HOST_SCHEMA = "OpenRemaster.ContinuationInspector.Response.v1"
K003_SCHEMA = "OpenRemaster.K003.AdmissionReceipt.v1"
REPORT_SCHEMA = "OpenRemaster.R06.LiveAuthorityIntakeReport.v1"
MANIFEST_SCHEMA = "OpenRemaster.R06.LiveAuthorityEvidenceManifest.v1"


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nonempty(value: Any) -> bool:
    return value is not None and value != ""


def truthy_marker(obj: dict[str, Any], *names: str) -> bool:
    return any(obj.get(name) is True for name in names)


def text(obj: dict[str, Any], *names: str) -> str:
    for name in names:
        value = obj.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def resolve_path(explicit: Path | None, evidence_dir: Path | None, names: tuple[str, ...]) -> Path | None:
    if explicit is not None:
        return explicit
    if evidence_dir is None:
        return None
    for name in names:
        candidate = evidence_dir / name
        if candidate.is_file():
            return candidate
    return None


def within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def result(name: str, path: Path | None) -> dict[str, Any]:
    return {
        "name": name,
        "present": path is not None,
        "path": str(path.resolve()) if path is not None else None,
        "status": "MISSING" if path is None else "REJECTED",
        "checks": {},
        "failures": [],
    }


def check(row: dict[str, Any], key: str, condition: bool) -> None:
    row["checks"][key] = "PASS" if condition else "FAIL"
    if not condition:
        row["failures"].append(key)


def load_evidence(row: dict[str, Any], path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        payload = load(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        row["failures"].append(f"unreadable:{type(exc).__name__}")
        row["status"] = "REJECTED"
        return None
    if not isinstance(payload, dict):
        row["failures"].append("payload_not_object")
        row["status"] = "REJECTED"
        return None
    return payload


def validate_manifest(path: Path | None, expected: dict[str, str]) -> tuple[dict[str, Any], dict[str, Path]]:
    row = result("live_evidence_manifest", path)
    resolved: dict[str, Path] = {}
    payload = load_evidence(row, path)
    if payload is None:
        return row, resolved
    check(row, "schema", payload.get("schema") == MANIFEST_SCHEMA)
    check(row, "operation_binding", payload.get("operation_id") == expected["operation_id"])
    check(row, "work_package_binding", payload.get("work_package_sha256") == expected["work_package_sha256"])
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    manifest_root = path.parent.resolve() if path is not None else Path.cwd().resolve()
    required = ("host_health_receipt", "k003_admission_receipt", "signature_verification_result")
    for name in required:
        entry = artifacts.get(name) if isinstance(artifacts.get(name), dict) else {}
        artifact_path = entry.get("path")
        digest = entry.get("sha256")
        check(row, f"{name}_entry", bool(artifact_path) and isinstance(digest, str) and len(digest) == 64)
        if not artifact_path:
            continue
        candidate = (manifest_root / artifact_path).resolve() if not Path(artifact_path).is_absolute() else Path(artifact_path).resolve()
        check(row, f"{name}_rooted", within(candidate, manifest_root))
        check(row, f"{name}_present", candidate.is_file())
        if candidate.is_file() and isinstance(digest, str) and len(digest) == 64:
            check(row, f"{name}_sha256", sha256(candidate) == digest.lower())
        resolved[name] = candidate
    combined = artifacts.get("owner_witness_evidence") if isinstance(artifacts.get("owner_witness_evidence"), dict) else None
    separate = all(isinstance(artifacts.get(name), dict) for name in ("owner_receipt", "witness_receipt"))
    check(row, "owner_witness_mode", combined is not None or separate)
    if combined is not None:
        owner_entry = {"owner_witness_evidence": combined}
    elif separate:
        owner_entry = {"owner_receipt": artifacts["owner_receipt"], "witness_receipt": artifacts["witness_receipt"]}
    else:
        owner_entry = {}
    for name, entry in owner_entry.items():
        artifact_path = entry.get("path")
        digest = entry.get("sha256")
        check(row, f"{name}_entry", bool(artifact_path) and isinstance(digest, str) and len(digest) == 64)
        if not artifact_path:
            continue
        candidate = (manifest_root / artifact_path).resolve() if not Path(artifact_path).is_absolute() else Path(artifact_path).resolve()
        check(row, f"{name}_rooted", within(candidate, manifest_root))
        check(row, f"{name}_present", candidate.is_file())
        if candidate.is_file() and isinstance(digest, str) and len(digest) == 64:
            check(row, f"{name}_sha256", sha256(candidate) == digest.lower())
        resolved[name] = candidate
    if not row["failures"]:
        row["status"] = "PASS"
    else:
        row["status"] = "REJECTED"
    row["resolved_paths"] = {name: str(value) for name, value in resolved.items()}
    return row, resolved


def validate_host(path: Path | None, expected: dict[str, str]) -> dict[str, Any]:
    row = result("host_health_receipt", path)
    payload = load_evidence(row, path)
    if payload is None:
        return row
    check(row, "schema", payload.get("schema") == HOST_SCHEMA)
    status_text = f"{payload.get('status', '')} {payload.get('authority', '')}".upper()
    error = payload.get("error", {}) if isinstance(payload.get("error"), dict) else {}
    check(row, "not_replay_or_historical", not any(token in status_text for token in ("REPLAY_ONLY", "PRODUCTION_HOLD", "UNSIGNED", "HISTORICAL")))
    check(row, "not_fixture_only", payload.get("fixture_only") is not True)
    check(row, "no_stale_snapshot", error.get("code") not in {"SNAPSHOT_CHANGED", "STALE_GENERATION"})
    check(row, "live_receipt_marker", truthy_marker(payload, "live_receipt") or payload.get("authority_scope") in {"HOST_LIVE", "LIVE_HOST"})
    generation = payload.get("generation", payload.get("fence_generation"))
    fence = payload.get("fence", payload.get("fence_epoch", payload.get("fence_id")))
    check(row, "current_generation_present", nonempty(generation))
    check(row, "current_fence_present", nonempty(fence))
    freshness = payload.get("freshness") if isinstance(payload.get("freshness"), dict) else {}
    check(row, "freshness_verified", truthy_marker(payload, "freshness_verified") or freshness.get("status") == "FRESH")
    project_id = text(payload, "project_id", "allowed_project_id")
    check(row, "project_binding", project_id == expected["project_id"])
    check(row, "path_allowlist_verified", truthy_marker(payload, "path_allowed", "allowed_path", "allowed_paths_verified"))
    check(row, "signature_or_secure_channel_marker", truthy_marker(payload, "signature_verified", "secure_channel_verified") or payload.get("authority_scope") in {"HOST_LIVE", "LIVE_HOST"})
    row["status"] = "PASS" if not row["failures"] else "REJECTED"
    return row


def validate_k003(path: Path | None, expected: dict[str, str]) -> dict[str, Any]:
    row = result("k003_admission_receipt", path)
    payload = load_evidence(row, path)
    if payload is None:
        return row
    check(row, "schema", payload.get("schema") == K003_SCHEMA)
    check(row, "decision_admit", payload.get("decision") == "ADMIT")
    for field in ("authority_authenticated", "owner_admitted", "witness_admitted", "fence_verified"):
        check(row, field, payload.get(field) is True)
    check(row, "production_go_false", payload.get("production_go") is False)
    check(row, "fixture_only_false", payload.get("fixture_only") is not True)
    check(row, "live_receipt_marker", payload.get("live_receipt") is True)
    check(row, "live_authority_scope", payload.get("authority_scope") == "K003_LIVE")
    check(row, "receipt_signature_present", nonempty(payload.get("receipt_signature")))
    for field in ("lease_id", "lease_nonce", "fence_epoch", "fence_generation"):
        check(row, f"{field}_present", nonempty(payload.get(field)))
    for field in ("operation_id", "work_package_sha256", "project_id", "capability"):
        check(row, f"binding_{field}", payload.get(field) == expected[field])
    dev_text = f"{payload.get('issuer', '')} {payload.get('environment', '')} {payload.get('signature_type', '')}".upper()
    check(row, "not_development_self_signed", payload.get("development_only") is not True and not any(token in dev_text for token in ("SELF_SIGNED", "D7", "DEV_ONLY")))
    row["status"] = "PASS" if not row["failures"] else "REJECTED"
    return row


def validate_principal(path: Path, role: str, expected: dict[str, str]) -> dict[str, Any]:
    row = result(f"{role.lower()}_receipt", path)
    payload = load_evidence(row, path)
    if payload is None:
        return row
    check(row, "schema_present", isinstance(payload.get("schema"), str) and bool(payload.get("schema", "").strip()))
    role_text = f"{payload.get('role', '')} {payload.get('authority_role', '')}".upper()
    check(row, "role_matches", role.upper() in role_text)
    admitted = payload.get("admitted") is True or payload.get(f"{role.lower()}_admitted") is True
    check(row, "admitted", admitted)
    check(row, "operation_binding", payload.get("operation_id") == expected["operation_id"])
    check(row, "work_package_binding", payload.get("work_package_sha256") == expected["work_package_sha256"])
    check(row, "independence_verified", payload.get("independence_verified") is True or payload.get("independent") is True)
    check(row, "not_same_process_self_attestation", payload.get("same_process_self_attestation") is not True)
    check(row, "not_unsigned_local_fixture", payload.get("unsigned_local_fixture") is not True and payload.get("fixture_only") is not True)
    scope_text = f"{payload.get('authority_scope', '')} {payload.get('environment', '')}".upper()
    check(row, "not_development_scope", not any(token in scope_text for token in ("DEV", "LOCAL", "SELF_SIGNED", "FIXTURE")))
    row["status"] = "PASS" if not row["failures"] else "REJECTED"
    return row


def validate_authority_pair(
    combined_path: Path | None,
    owner_path: Path | None,
    witness_path: Path | None,
    expected: dict[str, str],
) -> dict[str, Any]:
    if combined_path is not None:
        row = result("owner_witness_evidence", combined_path)
        payload = load_evidence(row, combined_path)
        if payload is None:
            return row
        check(row, "operation_binding", payload.get("operation_id") == expected["operation_id"])
        check(row, "work_package_binding", payload.get("work_package_sha256") == expected["work_package_sha256"])
        check(row, "owner_admitted", payload.get("owner_admitted") is True)
        check(row, "witness_admitted", payload.get("witness_admitted") is True)
        check(row, "independence_verified", payload.get("independence_verified") is True)
        check(row, "not_same_process_self_attestation", payload.get("same_process_self_attestation") is not True)
        check(row, "not_unsigned_local_fixture", payload.get("unsigned_local_fixture") is not True and payload.get("fixture_only") is not True)
        row["status"] = "PASS" if not row["failures"] else "REJECTED"
        return row

    row = result("owner_witness_evidence", owner_path or witness_path)
    row["paths"] = {
        "owner_receipt": str(owner_path.resolve()) if owner_path is not None else None,
        "witness_receipt": str(witness_path.resolve()) if witness_path is not None else None,
    }
    if owner_path is None and witness_path is None:
        return row
    owner_row = validate_principal(owner_path, "OWNER", expected) if owner_path is not None else result("owner_receipt", None)
    witness_row = validate_principal(witness_path, "WITNESS", expected) if witness_path is not None else result("witness_receipt", None)
    row["subevidence"] = {"owner_receipt": owner_row, "witness_receipt": witness_row}
    if owner_path is None:
        row["failures"].append("owner_receipt_missing")
    if witness_path is None:
        row["failures"].append("witness_receipt_missing")
    if owner_row.get("status") != "PASS":
        row["failures"].append("owner_receipt_rejected")
    if witness_row.get("status") != "PASS":
        row["failures"].append("witness_receipt_rejected")
    row["status"] = "PASS" if not row["failures"] else "REJECTED"
    return row


def validate_signature(path: Path | None, k003_path: Path | None, expected: dict[str, str]) -> dict[str, Any]:
    row = result("signature_verification_result", path)
    payload = load_evidence(row, path)
    if payload is None:
        return row
    check(row, "verified", payload.get("verified") is True or payload.get("signature_verified") is True)
    key_id = text(payload, "key_identity", "key_id", "signer_identity")
    check(row, "key_identity_present", bool(key_id))
    check(row, "verification_time_present", bool(text(payload, "verified_at", "verification_time", "verified_utc")))
    check(row, "verification_method_present", bool(text(payload, "verification_method", "method")))
    digest = text(payload, "verified_payload_digest", "payload_digest", "receipt_sha256")
    expected_digests = set()
    if k003_path is not None and k003_path.is_file():
        expected_digests.add(sha256(k003_path))
        try:
            k003_payload = load(k003_path)
            if isinstance(k003_payload, dict):
                for field in ("receipt_sha256", "payload_sha256", "signed_payload_sha256"):
                    if isinstance(k003_payload.get(field), str):
                        expected_digests.add(k003_payload[field])
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
    check(row, "verified_payload_digest", bool(digest) and digest in expected_digests)
    check(row, "operation_binding", payload.get("operation_id") == expected["operation_id"])
    check(row, "work_package_binding", payload.get("work_package_sha256") == expected["work_package_sha256"])
    method_text = f"{key_id} {text(payload, 'verification_method', 'method')}".upper()
    check(row, "not_development_self_signed", payload.get("self_signed") is not True and not any(token in method_text for token in ("SELF_SIGNED", "DEV_ONLY", "D7")))
    row["status"] = "PASS" if not row["failures"] else "REJECTED"
    return row


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=root / "outputs" / "OpenRemaster-R06-live-receipt-intake-contract-2026-10-24.json")
    parser.add_argument("--packet", type=Path, default=root / "outputs" / "OpenRemaster-R06-admission-packet-2026-10-24.json")
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--evidence-manifest", type=Path, help="Optional manifest declaring relative evidence paths and SHA-256 digests")
    parser.add_argument("--host-health-receipt", type=Path)
    parser.add_argument("--k003-admission-receipt", type=Path)
    parser.add_argument("--owner-witness-evidence", type=Path)
    parser.add_argument("--owner-receipt", type=Path)
    parser.add_argument("--witness-receipt", type=Path)
    parser.add_argument("--signature-verification", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    failures: list[str] = []
    contract = load(args.contract)
    packet = load(args.packet)
    packet_sha = sha256(args.packet)
    work_package = packet.get("work_package", {}) if isinstance(packet, dict) else {}
    expected = {
        "operation_id": packet.get("operation_id") if isinstance(packet, dict) else "",
        "work_package_sha256": packet.get("work_package_sha256") if isinstance(packet, dict) else "",
        "project_id": work_package.get("project_id", "") if isinstance(work_package, dict) else "",
        "capability": work_package.get("capability", "") if isinstance(work_package, dict) else "",
    }
    contract_packet = contract.get("admission_packet", {}) if isinstance(contract, dict) else {}
    canonical_checks = {
        "contract_schema": isinstance(contract, dict) and contract.get("schema") == "OpenRemaster.R06.LiveReceiptIntakeContract.v1",
        "packet_schema": isinstance(packet, dict) and packet.get("schema") == "OpenRemaster.R06.AdmissionPacket.v1",
        "packet_hash_matches_contract": packet_sha == contract_packet.get("sha256"),
        "operation_matches_contract": expected["operation_id"] == contract_packet.get("operation_id"),
        "work_package_matches_contract": expected["work_package_sha256"] == contract_packet.get("work_package_sha256"),
        "packet_dispatch_false": isinstance(packet, dict) and packet.get("dispatch_authorized") is False,
        "packet_production_false": isinstance(packet, dict) and packet.get("production_go") is False,
    }
    for key, condition in canonical_checks.items():
        if not condition:
            failures.append(f"canonical:{key}")

    evidence_dir = args.evidence_dir.resolve() if args.evidence_dir is not None else None
    manifest_row, manifest_paths = validate_manifest(args.evidence_manifest, expected) if args.evidence_manifest is not None else (result("live_evidence_manifest", None), {})
    host_path = args.host_health_receipt or manifest_paths.get("host_health_receipt") or resolve_path(None, evidence_dir, ("host_health_receipt.json", "host-health-receipt.json", "host.json"))
    k003_path = args.k003_admission_receipt or manifest_paths.get("k003_admission_receipt") or resolve_path(None, evidence_dir, ("k003_admission_receipt.json", "k003-admission-receipt.json", "k003.json"))
    owner_witness_path = args.owner_witness_evidence or manifest_paths.get("owner_witness_evidence") or resolve_path(None, evidence_dir, ("owner_witness_evidence.json", "owner-witness-evidence.json", "owner-witness.json"))
    owner_receipt_path = args.owner_receipt or manifest_paths.get("owner_receipt") or resolve_path(None, evidence_dir, ("owner_receipt.json", "owner-receipt.json", "owner-attestation.json"))
    witness_receipt_path = args.witness_receipt or manifest_paths.get("witness_receipt") or resolve_path(None, evidence_dir, ("witness_receipt.json", "witness-receipt.json", "witness-attestation.json"))
    signature_path = args.signature_verification or manifest_paths.get("signature_verification_result") or resolve_path(None, evidence_dir, ("signature_verification_result.json", "signature-verification-result.json", "signature.json"))

    rows = {
        "host_health_receipt": validate_host(host_path, expected),
        "k003_admission_receipt": validate_k003(k003_path, expected),
        "owner_witness_evidence": validate_authority_pair(owner_witness_path, owner_receipt_path, witness_receipt_path, expected),
        "signature_verification_result": validate_signature(signature_path, k003_path, expected),
    }
    missing = [name for name, row in rows.items() if not row["present"]]
    rejected = [name for name, row in rows.items() if row["present"] and row["status"] != "PASS"]
    for name in missing:
        failures.append(f"missing:{name}")
    for name in rejected:
        failures.append(f"rejected:{name}")
    if args.evidence_manifest is not None and manifest_row["status"] != "PASS":
        failures.append("rejected:live_evidence_manifest")

    all_pass = not failures and not missing and not rejected
    if all_pass:
        status = "PASS_LIVE_AUTHORITY_INTAKE_NO_DISPATCH"
    elif missing and not rejected and not [item for item in failures if item.startswith("canonical:")]:
        status = "WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE"
    else:
        status = "HOLD_BEFORE_DISPATCH"

    report = {
        "schema": REPORT_SCHEMA,
        "validator": str(Path(__file__).resolve()),
        "validator_sha256": sha256(Path(__file__).resolve()),
        "status": status,
        "authority_scope": "external evidence intake only; no authority transfer",
        "canonical": {
            "contract": str(args.contract.resolve()),
            "packet": str(args.packet.resolve()),
            "packet_sha256_observed": packet_sha,
            "operation_id": expected["operation_id"],
            "work_package_sha256": expected["work_package_sha256"],
            "project_id": expected["project_id"],
            "capability": expected["capability"],
            "checks": canonical_checks,
        },
        "manifest": manifest_row,
        "evidence": rows,
        "missing_external_evidence": missing,
        "rejected_external_evidence": rejected,
        "failures": failures,
        "intake_ready": all_pass,
        "authority_bound": False,
        "signature_verification_performed_by_validator": False,
        "synthetic_evidence_created": False,
        "dispatch_authorized": False,
        "dispatch_performed": False,
        "worker_started_by_validator": False,
        "production_go": False,
        "read_only": True,
        "next_gate": "Keep HOLD until all four external artifacts pass; then run the consolidated R06 gate evaluator with independent crypto verification. Never dispatch from this report alone.",
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if status in {"WAITING_FOR_EXTERNAL_AUTHORITY_EVIDENCE", "PASS_LIVE_AUTHORITY_INTAKE_NO_DISPATCH"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
