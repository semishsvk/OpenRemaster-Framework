"""Validate proposal freshness and job admission before any ORCH-K003 invocation.
This module has no subprocess or worker execution capability.
"""
import hashlib,json
from pathlib import Path
from dynamic_scheduler_queue_v1 import canonical
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_dispatch(proposal_path,pool_path,capacity_path,job_path,worker_id):
    p=json.loads(Path(proposal_path).read_text(encoding="utf-8"))
    if p.get("schema")!="OpenRemaster.DispatchProposal.v1" or p.get("status")!="PLAN_ONLY":
        return {"status":"BLOCKED","reason":"INVALID_PROPOSAL"}
    if p.get("dispatch_executed") is not False or p.get("approval")!="NOT_GRANTED_BY_PROPOSAL":
        return {"status":"BLOCKED","reason":"INVALID_PROPOSAL_STATE"}
    if p["source_sha256"]!={"pool":sha(pool_path),"capacity":sha(capacity_path)}:
        return {"status":"BLOCKED","reason":"STALE_INPUT"}
    cap=json.loads(Path(capacity_path).read_text(encoding="utf-8"))
    if not all(cap.get(k) is True for k in ("complete","fresh","source_authorized")):
        return {"status":"BLOCKED","reason":"CAPACITY_NOT_AUTHORITATIVE"}
    job=json.loads(Path(job_path).read_text(encoding="utf-8"))
    if job.get("schema")!="ORCH-K003.Job.v1":
        return {"status":"BLOCKED","reason":"INVALID_JOB"}
    matches=[a for a in p["result"]["assignments"] if a["task_id"]==job.get("task") and a["project"]==job.get("project") and a["worker_id"]==worker_id]
    if len(matches)!=1:return {"status":"BLOCKED","reason":"UNASSIGNED_JOB"}
    if job.get("job_id") is None or not job.get("required_capabilities") or not isinstance(job.get("execution"),dict):
        return {"status":"BLOCKED","reason":"INCOMPLETE_JOB"}
    if job["execution"].get("kind") not in ("godot_runtime","executable_runtime"):
        return {"status":"BLOCKED","reason":"UNSUPPORTED_EXECUTION"}
    workers=[w for w in cap["workers"] if w["worker_id"]==worker_id]
    if len(workers)!=1 or not workers[0].get("commissioned") or not workers[0].get("available"):
        return {"status":"BLOCKED","reason":"WORKER_NOT_READY"}
    if not set(job["required_capabilities"]).issubset(workers[0]["capabilities"]):
        return {"status":"BLOCKED","reason":"CAPABILITY_MISMATCH"}
    return {"status":"READY_FOR_SEPARATE_ADMISSION","job_sha256":sha(job_path),
            "proposal_sha256":sha(proposal_path),"worker_id":worker_id,
            "note":"No lease acquired and no execution authorized by this result"}
