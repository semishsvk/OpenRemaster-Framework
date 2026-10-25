"""CausalFidelityDiff.v1: evidence-ranked candidate causes, not causal guesses."""
from alignment import is_hash, finite

LAYERS = {"camera", "geometry", "uv", "palette", "objects", "animations",
          "hud", "audio", "timing", "input", "state", "lighting", "transparency"}


def analyze_causes(admission_result, observations):
    if not isinstance(admission_result, dict) or admission_result.get("status") != "ADMISSIBLE":
        return {"schema": "CausalFidelityDiff.v1", "status": "ALIGNMENT_BLOCKED",
                "findings": [], "fidelity_verified": False}
    if not isinstance(observations, list):
        return {"schema": "CausalFidelityDiff.v1", "status": "INSUFFICIENT_EVIDENCE",
                "findings": [], "fidelity_verified": False}
    findings = []
    for row in observations:
        if not isinstance(row, dict):
            findings.append({"status": "INVALID_OBSERVATION"})
            continue
        layer = row.get("layer")
        result = {"layer": layer, "mechanism": row.get("mechanism"), "status": "HYPOTHESIS"}
        if not isinstance(layer, str) or layer not in LAYERS or not isinstance(row.get("mechanism"), str) or not row["mechanism"]:
            result["status"] = "INVALID_OBSERVATION"
        elif (is_hash(row.get("source_mechanism_sha256")) and
              is_hash(row.get("oracle_frame_sha256")) and
              is_hash(row.get("candidate_frame_sha256")) and
              is_hash(row.get("comparison_evidence_sha256")) and
              finite(row.get("error_before")) and finite(row.get("error_after")) and
              row["error_before"] >= 0 and row["error_after"] >= 0 and
              row.get("controlled_intervention") is True and
              row.get("independent_repeat") is True):
            before, after = row["error_before"], row["error_after"]
            result["status"] = ("SUPPORTED_CAUSE" if after < before else
                                "REFUTED_FOR_THIS_TEST" if after > before else "NO_DETECTABLE_EFFECT")
            result["error_reduction"] = round(before - after, 8)
        findings.append(result)
    return {"schema": "CausalFidelityDiff.v1",
            "status": "EVALUATED" if all(x["status"] != "INVALID_OBSERVATION" for x in findings)
                      else "PARTIAL_INVALID",
            "findings": findings, "fidelity_verified": False}


def promotion_readiness(admission_result, comparator):
    """Only an eligibility decision. Actual fidelity PASS remains with independent
    ORCH-K003 validator and game-specific acceptance contracts."""
    if not isinstance(admission_result, dict) or admission_result.get("status") != "ADMISSIBLE":
        return {"schema": "FidelityPromotionGuard.v1", "status": "BLOCKED_ALIGNMENT",
                "fidelity_verified": False}
    if not isinstance(comparator, dict):
        return {"schema": "FidelityPromotionGuard.v1", "status": "INSUFFICIENT_COMPARATOR",
                "fidelity_verified": False}
    required = ("source_capture_sha256", "candidate_capture_sha256",
                "comparator_attestation_sha256", "runtime_replay_sha256")
    if (comparator.get("schema") != "IndependentFidelityComparison.v1" or
        comparator.get("status") not in ("PASS", "FAIL") or
        comparator.get("independent_reverification") is not True or
        any(not is_hash(comparator.get(k)) for k in required) or
        comparator.get("source_capture_sha256", "").lower() !=
            str(admission_result.get("source_capture_sha256", "")).lower() or
        comparator.get("candidate_capture_sha256", "").lower() !=
            str(admission_result.get("candidate_capture_sha256", "")).lower()):
        return {"schema": "FidelityPromotionGuard.v1", "status": "INSUFFICIENT_COMPARATOR",
                "fidelity_verified": False}
    if comparator["status"] == "FAIL":
        return {"schema": "FidelityPromotionGuard.v1",
                "status": "VALID_FIDELITY_FAIL", "fidelity_verified": False}
    if comparator.get("all_required_layers_covered") is not True:
        return {"schema": "FidelityPromotionGuard.v1",
                "status": "INSUFFICIENT_COMPARATOR", "fidelity_verified": False}
    return {"schema": "FidelityPromotionGuard.v1",
            "status": "ELIGIBLE_FOR_EXTERNAL_ACCEPTANCE",
            "fidelity_verified": False}
