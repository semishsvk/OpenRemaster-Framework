"""Non-invasive opt-in ORCH-K003 adapter.

This module wraps, but never replaces, the existing independent validator.
When this adapter is selected, every fidelity_runtime job MUST supply matched
original/reconstruction capture evidence. No silent fallback to vanilla PASS.
"""
import json
from pathlib import Path

from alignment import admissibility, hash_file, is_hash
from causal import promotion_readiness


def gated_validate(job, result_path, base_validate):
    """Inject existing validator.validate as base_validate callable.
    Not the live ORCH-K003 entry point until the integration owner promotes it.
    """
    base = base_validate(job, result_path)
    if base.get("status") != "PASS":
        return base
    validation = job.get("validation") or {}
    required = (job.get("execution", {}).get("kind") == "fidelity_runtime" or
                validation.get("require_scene_alignment") is True)
    if not required:
        return base
    output = dict(base)
    output.setdefault("failures", [])
    receipt_dir = Path(result_path).resolve().parent
    detail = validation.get("oracle_alignment")
    if not isinstance(detail, dict):
        output["status"] = "FAIL"
        output["failures"] = list(output["failures"]) + ["ORACLE_ALIGNMENT_EVIDENCE_MISSING"]
        return output
    name = detail.get("manifest_name")
    expected = detail.get("manifest_sha256")
    if (not isinstance(name, str) or not name or
        name != Path(name).name or not name.lower().endswith(".json") or
        not is_hash(expected)):
        output["status"] = "FAIL"
        output["failures"] = list(output["failures"]) + ["ORACLE_ALIGNMENT_MANIFEST_INVALID"]
        return output
    try:
        manifest_path = (receipt_dir / name).resolve(strict=True)
        if manifest_path.parent != receipt_dir or hash_file(manifest_path).lower() != expected.lower():
            raise ValueError("MANIFEST_OUTSIDE_RUN_OR_HASH_MISMATCH")
        bundle = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        roots = detail.get("roots")
        guard = admissibility(bundle, roots)
        output["oracle_admissibility"] = guard
        output["fidelity_verified"] = False
        if guard.get("status") != "ADMISSIBLE":
            output["status"] = "FAIL"
            output["failures"] = list(output["failures"]) + [
                "ORACLE_ALIGNMENT_" + guard["reason"]]
        comparison = detail.get("independent_comparison")
        if comparison and output.get("status") == "PASS":
            readiness = promotion_readiness(guard, comparison)
            output["fidelity_readiness"] = readiness
            if readiness["status"] == "VALID_FIDELITY_FAIL":
                output["status"] = "FAIL"
                output["failures"] = list(output["failures"]) + ["FIDELITY_COMPARISON_DIFFERENCE"]
            elif readiness["status"] != "ELIGIBLE_FOR_EXTERNAL_ACCEPTANCE":
                output["status"] = "FAIL"
                output["failures"] = list(output["failures"]) + ["COMPARISON_NOT_ADMISSIBLE"]
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        output["status"] = "FAIL"
        output["failures"] = list(output["failures"]) + ["ORACLE_ALIGNMENT_INDEPENDENT_CHECK_FAILED"]
        output["alignment_error_type"] = type(exc).__name__
    return output
