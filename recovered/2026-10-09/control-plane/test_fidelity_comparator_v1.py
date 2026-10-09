"""Pure synthetic fixtures: independent byte-comparison canary, NOT game-fidelity evidence."""
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fidelity_runtime_isolation_v1 import sha256,IsolationError
from fidelity_runtime_worker_v1 import validate_comparison,ROOT

def fail(expected,fn):
    try: fn()
    except IsolationError as e:
        assert e.reason==expected,(expected,e.reason)
        return
    raise AssertionError("Expected "+expected)

with tempfile.TemporaryDirectory(prefix="fidelity-comparator-fixture-",dir=ROOT/"runtime-test"/"results") as td:
    root=Path(td)
    orig=root/"original"/"capture"
    curr=root/"reconstructed"/"capture"
    orig.mkdir(parents=True)
    curr.mkdir(parents=True)
    frame=b"\x89PNG\r\n\x1a\nSYNTHETIC_CANARY_BYTES_NOT_A_REAL_GAME_FRAME"
    (orig/"frame.png").write_bytes(frame)
    (curr/"frame.png").write_bytes(frame)
    h=sha256(orig/"frame.png")
    original_manifest={
        "schema":"FidelityLocalCaptureAttestation.v1","backend":"windows_graphics_capture",
        "remote_desktop_capture_authority":False,"pid":100,"hwnd":200,
        "creation_ticks_100ns":500,"run_token":"old","executable_sha256":"sourcedummy",
        "frames":[{"path":"frame.png","sha256":h}]}
    op=orig/"capture-attestation.json"
    op.write_text(json.dumps(original_manifest))
    capture_evidence={"manifest_sha256":"fixture_current_sha","frames":[{"path":str(curr/"frame.png"),"sha256":h}],"audio":[]}
    evidence={
        "schema":"FidelityIndependentComparison.v1","status":"PASS",
        "capture_manifest_sha256":capture_evidence["manifest_sha256"],
        "original_capture_manifest_path":str(op),
        "original_capture_manifest_sha256":sha256(op),
        "mode":"SHA256_BYTE_EXACT","comparator":"FidelityByteExact.v1"}
    cp=curr/"comparison-attestation.json"
    cp.write_text(json.dumps(evidence))
    accepted=validate_comparison(curr,capture_evidence)
    assert accepted["verified_frame_count"]==1
    capture_evidence["frames"][0]["sha256"]="different"
    fail("FIDELITY_BYTE_MISMATCH",lambda:validate_comparison(curr,capture_evidence))
    evidence["mode"]="SELF_ATTESTED_PASS"
    cp.write_text(json.dumps(evidence))
    fail("INDEPENDENT_COMPARATOR_NOT_SUPPORTED",lambda:validate_comparison(curr,capture_evidence))
    print(json.dumps({"schema":"FidelityComparisonSyntheticCanary.v1","status":"PASS",
           "synthetic_byte_identical":"PASS","mismatch_rejected":"PASS",
           "self_attestation_rejected":"PASS","actual_game_fidelity":"NOT_TESTED"}))
