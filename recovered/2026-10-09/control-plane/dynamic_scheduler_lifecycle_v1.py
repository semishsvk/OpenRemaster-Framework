"""Pure state-transition model for a future native scheduler adapter.
No subprocess, clock, lease, file or worker side effects.
"""
TERMINAL={"PASS","FAIL","BLOCKED","CANCELLED"}
ALLOWED={
 "PROPOSED":{"ADMISSION_PENDING"},
 "ADMISSION_PENDING":{"ADMITTED","BLOCKED"},
 "ADMITTED":{"LEASED","BLOCKED"},
 "LEASED":{"RUNNING","BLOCKED"},
 "RUNNING":{"VALIDATING","BLOCKED"},
 "VALIDATING":{"PASS","FAIL","BLOCKED"},
}
def transition(state,event,evidence):
    if state in TERMINAL or event not in ALLOWED.get(state,set()):
        return {"status":"BLOCKED","reason":"ILLEGAL_TRANSITION"}
    if not isinstance(evidence,dict) or evidence.get("verified") is not True:
        return {"status":"BLOCKED","reason":"MISSING_VERIFIED_EVIDENCE"}
    required={
      "ADMITTED":("admission_id","worker_id"),
      "LEASED":("lease_id","fencing_epoch"),
      "RUNNING":("pid","start_utc"),
      "VALIDATING":("exit_code","result_sha256"),
      "PASS":("validation_sha256","checkpoint_sha256","process_tree_stopped"),
      "FAIL":("validation_sha256","process_tree_stopped"),
      "BLOCKED":("reason","process_tree_stopped"),
    }
    if any(evidence.get(k) is None or evidence.get(k)=="" for k in required.get(event,())):
        return {"status":"BLOCKED","reason":"INCOMPLETE_TRANSITION_EVIDENCE"}
    if event in TERMINAL and evidence.get("process_tree_stopped") is not True:
        return {"status":"BLOCKED","reason":"PROCESS_NOT_RECONCILED"}
    return {"status":"ACCEPTED","from":state,"to":event}
def recovery_action(snapshot):
    if not isinstance(snapshot,dict) or snapshot.get("source_hash_verified") is not True:
        return "QUARANTINE"
    if snapshot.get("state") in TERMINAL:return "REUSE_TERMINAL"
    if snapshot.get("process_tree_status")!="STOPPED_VERIFIED":
        return "BLOCKED_RECONCILE_PROCESS_TREE"
    if snapshot.get("lease_status")!="RELEASED_VERIFIED":
        return "BLOCKED_RECONCILE_LEASE"
    if not snapshot.get("checkpoint_verified"):return "BLOCKED_REHYDRATION"
    return "ELIGIBLE_FOR_NEW_ADMISSION"
