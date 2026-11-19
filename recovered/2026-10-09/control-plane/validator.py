import hashlib, json
from pathlib import Path

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()

def validate(job, result_path):
    p=Path(result_path)
    failures=[]
    if not p.is_file():
        return {"schema":"ORCH-K003.ValidationResult.v1","status":"FAIL","failures":["RESULT_MISSING"]}
    try:
        result=json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception as e:
        return {"schema":"ORCH-K003.ValidationResult.v1","status":"FAIL","failures":["RESULT_INVALID_JSON"],"error":str(e)}
    expected=job.get("validation",{}).get("expected_exit_code")
    if result.get("exit_code") != expected:
        failures.append("EXIT_CODE_MISMATCH")
    if result.get("status") != "PASS":
        failures.append("WORKER_RESULT_NOT_PASS")
    fp=result.get("fingerprint",{})
    if job.get("execution",{}).get("kind")=="godot_runtime":
        if not fp.get("godot_sha256"): failures.append("GODOT_FINGERPRINT_MISSING")
        if not fp.get("project_godot_sha256"): failures.append("PROJECT_FINGERPRINT_MISSING")
        if fp.get("remote_desktop_capture_authority") is not False:
            failures.append("REMOTE_DESKTOP_AUTHORITY_INVALID")
    if job.get("execution",{}).get("kind")=="fidelity_runtime":
        if result.get("schema")!="FidelityRuntimeResult.v1":
            failures.append("FIDELITY_RESULT_SCHEMA_INVALID")
        if result.get("capture_authority")!="LOCAL_ONLY" or result.get("remote_desktop_capture_authority") is not False:
            failures.append("FIDELITY_CAPTURE_AUTHORITY_INVALID")
        identity=result.get("runtime_identity") or {}
        if not identity.get("pid") or not identity.get("creation_ticks_100ns") or not identity.get("executable_sha256"):
            failures.append("FIDELITY_RUNTIME_IDENTITY_MISSING")
        if not (result.get("runtime_window") or {}).get("hwnd"):
            failures.append("FIDELITY_OWNED_HWND_MISSING")
        capture=result.get("capture_evidence") or {}
        comparison=result.get("comparison_evidence") or {}
        capture_root=p.parent/"fidelity-isolated"/"capture"
        if not capture.get("manifest_sha256") or not comparison.get("attestation_sha256"):
            failures.append("FIDELITY_EVIDENCE_MISSING")
        else:
            cm=capture_root/"capture-attestation.json"
            cp=capture_root/"comparison-attestation.json"
            if not cm.is_file() or sha(cm)!=capture["manifest_sha256"]:
                failures.append("FIDELITY_CAPTURE_MANIFEST_STALE")
            if not cp.is_file() or sha(cp)!=comparison["attestation_sha256"]:
                failures.append("FIDELITY_COMPARISON_ATTESTATION_STALE")
            for row in capture.get("frames",[])+capture.get("audio",[]):
                f=Path(row.get("path","")).resolve()
                if capture_root.resolve() not in f.parents or not f.is_file() or sha(f)!=row.get("sha256"):
                    failures.append("FIDELITY_ARTIFACT_NOT_AUTHENTIC")
                    break
        if result.get("preflight_conflicts"):
            failures.append("FIDELITY_GUI_CONFLICT")
        # Independently reopen all manifests and re-run the byte comparator.
        # A worker-authored JSON field claiming PASS is never sufficient.
        if capture.get("manifest_sha256") and comparison.get("attestation_sha256") and identity.get("pid"):
            try:
                from fidelity_runtime_worker_v1 import validate_capture, validate_comparison
                from fidelity_runtime_isolation_v1 import IsolationError
                proven=validate_capture(capture_root,identity,result.get("runtime_window") or {},
                                         result.get("epoch"),bool(job.get("execution",{}).get("require_audio",False)))
                checked=validate_comparison(capture_root,proven)
                if proven["manifest_sha256"]!=capture["manifest_sha256"]:
                    failures.append("FIDELITY_CAPTURE_PROOF_MISMATCH")
                if checked["attestation_sha256"]!=comparison["attestation_sha256"]:
                    failures.append("FIDELITY_COMPARATOR_PROOF_MISMATCH")
            except (IsolationError,OSError,ValueError,KeyError,json.JSONDecodeError) as exc:
                failures.append("FIDELITY_INDEPENDENT_REVERIFY_FAILED:"+getattr(exc,"reason",type(exc).__name__))
    return {"schema":"ORCH-K003.ValidationResult.v1","status":"PASS" if not failures else "FAIL",
            "failures":failures,"worker_result_sha256":sha(p),"expected_exit_code":expected,
            "observed_exit_code":result.get("exit_code")}
