import hashlib,json
from pathlib import Path

def operation_id(job):
    stable={"job_id":job["job_id"],"project":job["project"],"task":job["task"],
            "execution":job["execution"],"required_capabilities":job["required_capabilities"]}
    return hashlib.sha256(json.dumps(stable,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def reconcile(result_path, expected_operation_id=None):
    p=Path(result_path)
    if not p.is_file():
        return {"action":"EXECUTE","reason":"NO_RESULT"}
    try:
        result=json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {"action":"QUARANTINE","reason":"INVALID_RESULT"}
    observed=result.get("operation_id")
    if expected_operation_id and observed and observed != expected_operation_id:
        return {"action":"QUARANTINE","reason":"OPERATION_ID_MISMATCH","observed":observed}
    if result.get("status") in ("PASS","FAIL") and result.get("exit_code") is not None:
        return {"action":"REUSE_RESULT","reason":"TERMINAL_RESULT_PRESENT","status":result.get("status")}
    return {"action":"QUARANTINE","reason":"AMBIGUOUS_RESULT"}
