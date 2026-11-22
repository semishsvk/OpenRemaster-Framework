"""OracleAlignmentContract.v1 + ComparisonAdmissibilityGuard.v1.
Pure independent validator. No runtime launching and no RDC-stream evidence.
"""
import hashlib
import math
from pathlib import Path
import re

HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
ORACLE_LEVELS = {"ALIGNED_ORACLE", "DETERMINISTIC_ORACLE", "FIDELITY_ATTESTED"}
CAPTURE_METHODS = {"LOCAL_FRAMEBUFFER", "LOCAL_RUNTIME_FILE", "NATIVE_WINDOW_CAPTURE"}
IDENTITY_KEYS = ("game", "scenario_id", "canonical_scene_id",
                 "capture_point_id", "replay_id", "input_trace_sha256")
CAMERA_FIELDS = ("position", "yaw_deg", "pitch_deg", "fov_deg",
                 "projection", "viewport", "canonical_space_sha256")


def hash_file(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def is_hash(value):
    return isinstance(value, str) and bool(HEX64.fullmatch(value))


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def safe_frame(root, frame):
    """Reopen original bytes and constrain the path to a trusted capture root."""
    if not isinstance(frame, dict) or not is_hash(frame.get("sha256")):
        return False, "FRAME_HASH_MISSING"
    name = frame.get("relative_path")
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        return False, "FRAME_PATH_INVALID"
    if ":" in name or "\\" in name or ".." in Path(name).parts:
        return False, "FRAME_PATH_INVALID"
    try:
        base = Path(root).resolve(strict=True)
        full = (base / name).resolve(strict=True)
        if base not in full.parents or not full.is_file():
            return False, "FRAME_OUTSIDE_TRUSTED_ROOT"
        if hash_file(full).lower() != frame["sha256"].lower():
            return False, "FRAME_HASH_MISMATCH"
    except (OSError, ValueError, TypeError):
        return False, "FRAME_UNAVAILABLE"
    return True, None


def angle_delta(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


def evaluate_alignment(bundle, roots=None):
    """Returns ALIGNED, ALIGNMENT_BLOCKED or INSUFFICIENT_EVIDENCE.
    Does not assert pixel or game-state fidelity.
    """
    missing, mismatches = [], []
    if not isinstance(bundle, dict) or bundle.get("schema") != "OracleAlignmentContract.v1":
        return {"schema": "OracleAlignmentResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "missing": ["ALIGNMENT_SCHEMA"], "mismatches": [], "pixel_diff_admissible": False}
    original, reconstructed = bundle.get("original"), bundle.get("reconstruction")
    policy = bundle.get("policy")
    if not isinstance(original, dict) or not isinstance(reconstructed, dict):
        return {"schema": "OracleAlignmentResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "missing": ["PAIRED_RUNTIME_RECORDS"], "mismatches": [], "pixel_diff_admissible": False}
    if not isinstance(policy, dict):
        policy = {}
    if policy.get("status") != "GAME_SPECIFIC_VALIDATED" or not is_hash(policy.get("evidence_sha256")):
        missing.append("VALIDATED_ALIGNMENT_POLICY")
    if not isinstance(roots, dict) or "policy" not in roots:
        missing.append("INDEPENDENT_POLICY_EVIDENCE_ROOT")
    else:
        valid_policy, _policy_error = safe_frame(
            roots["policy"],
            {"relative_path": policy.get("evidence_path"),
             "sha256": policy.get("evidence_sha256")})
        if not valid_policy:
            missing.append("ALIGNMENT_POLICY_EVIDENCE_INVALID")
    tolerances = {}
    for field in ("camera_position", "angle_deg", "fov_deg", "tick"):
        value = policy.get(field + "_tolerance")
        if not finite(value) or value < 0:
            missing.append("TOLERANCE_" + field.upper())
        else:
            tolerances[field] = float(value)

    for key in IDENTITY_KEYS:
        a, b = original.get(key), reconstructed.get(key)
        if a is None or b is None or (isinstance(a, str) and not a):
            missing.append("IDENTITY_" + key.upper())
        elif a != b:
            mismatches.append("IDENTITY_" + key.upper() + "_MISMATCH")
    for key in ("input_trace_sha256",):
        if not is_hash(original.get(key)) or not is_hash(reconstructed.get(key)):
            missing.append(key.upper() + "_HASH_INVALID")
    for side, record in (("ORIGINAL", original), ("RECONSTRUCTION", reconstructed)):
        if not is_hash(record.get("source_corpus_sha256")):
            missing.append(side + "_CORPUS_FINGERPRINT")
        if not is_hash(record.get("runtime_fingerprint_sha256")):
            missing.append(side + "_RUNTIME_FINGERPRINT")
        if record.get("capture_method") not in CAPTURE_METHODS:
            missing.append(side + "_LOCAL_CAPTURE_AUTHORITY")
        if record.get("remote_desktop_capture_authority") is not False:
            missing.append(side + "_RDC_NOT_AUTHORITY")
    if original.get("oracle_level") not in ORACLE_LEVELS:
        missing.append("ORIGINAL_ALIGNED_ORACLE_LEVEL")
    if (is_hash(original.get("source_corpus_sha256")) and
            is_hash(reconstructed.get("source_corpus_sha256")) and
            original["source_corpus_sha256"].lower() != reconstructed["source_corpus_sha256"].lower()):
        mismatches.append("SOURCE_CORPUS_MISMATCH")
    for key in ("tick",):
        a, b = original.get(key), reconstructed.get(key)
        if not finite(a) or not finite(b):
            missing.append("TICK_PROVENANCE")
        elif "tick" in tolerances and abs(a - b) > tolerances["tick"]:
            mismatches.append("TEMPORAL_TICK_MISMATCH")

    a_cam, b_cam = original.get("camera"), reconstructed.get("camera")
    if not isinstance(a_cam, dict) or not isinstance(b_cam, dict):
        missing.append("CAMERA_CONTRACT")
    else:
        for field in ("projection", "canonical_space_sha256", "viewport"):
            if a_cam.get(field) is None or b_cam.get(field) is None:
                missing.append("CAMERA_" + field.upper())
            elif a_cam[field] != b_cam[field]:
                mismatches.append("CAMERA_" + field.upper() + "_MISMATCH")
        if not is_hash(a_cam.get("canonical_space_sha256")) or not is_hash(b_cam.get("canonical_space_sha256")):
            missing.append("CAMERA_NORMALIZATION_PROVENANCE")
        av, bv = a_cam.get("position"), b_cam.get("position")
        if not (isinstance(av, list) and isinstance(bv, list) and
                len(av) == len(bv) == 3 and all(finite(v) for v in av + bv)):
            missing.append("CAMERA_POSITION")
        elif "camera_position" in tolerances and max(abs(x - y) for x, y in zip(av, bv)) > tolerances["camera_position"]:
            mismatches.append("CAMERA_POSITION_MISMATCH")
        for field in ("yaw_deg", "pitch_deg", "fov_deg"):
            x, y = a_cam.get(field), b_cam.get(field)
            if not finite(x) or not finite(y):
                missing.append("CAMERA_" + field.upper())
                continue
            limit = tolerances.get("fov_deg" if field == "fov_deg" else "angle_deg")
            delta = angle_delta(x, y) if field == "yaw_deg" else abs(x - y)
            if limit is not None and delta > limit:
                mismatches.append("CAMERA_" + field.upper() + "_MISMATCH")
        for cam in (a_cam, b_cam):
            viewport = cam.get("viewport")
            if not (isinstance(viewport, list) and len(viewport) == 2 and
                    all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in viewport)):
                missing.append("VALID_VIEWPORT")
            if not finite(cam.get("fov_deg")) or not 0 < cam["fov_deg"] < 180:
                missing.append("VALID_FOV")

    if not isinstance(roots, dict):
        missing.append("INDEPENDENT_CAPTURE_ROOTS")
    else:
        for key, record in (("original", original), ("reconstruction", reconstructed)):
            if key not in roots:
                missing.append(key.upper() + "_CAPTURE_ROOT")
                continue
            valid, error = safe_frame(roots[key], record.get("frame"))
            if not valid:
                missing.append(key.upper() + "_" + error)

    if mismatches:
        status = "ALIGNMENT_BLOCKED"
    elif missing:
        status = "INSUFFICIENT_EVIDENCE"
    else:
        status = "ALIGNED"
    return {"schema": "OracleAlignmentResult.v1", "status": status,
            "missing": sorted(set(missing)), "mismatches": sorted(set(mismatches)),
            "pixel_diff_admissible": status == "ALIGNED",
            "fidelity_verified": False}


def admissibility(bundle, roots=None):
    aligned = evaluate_alignment(bundle, roots)
    original = bundle.get("original", {}) if isinstance(bundle, dict) else {}
    reconstruction = bundle.get("reconstruction", {}) if isinstance(bundle, dict) else {}
    return {"schema": "ComparisonAdmissibilityGuard.v1",
            "status": "ADMISSIBLE" if aligned["status"] == "ALIGNED" else "BLOCKED",
            "reason": aligned["status"], "alignment": aligned,
            "source_capture_sha256": (original.get("frame") or {}).get("sha256"),
            "candidate_capture_sha256": (reconstruction.get("frame") or {}).get("sha256"),
            "may_report_fidelity_score": aligned["status"] == "ALIGNED",
            "fidelity_verified": False}
