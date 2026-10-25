"""Deterministic multi-cycle simulation; NEVER executes production jobs.
Each synthetic tick completes selected jobs with explicit simulated outcomes.
"""
from dynamic_scheduler_core_v1 import plan,Task,Worker
from dynamic_scheduler_lifecycle_v1 import transition
def simulate(tasks,workers,outcomes,max_ticks=100):
    pending=list(tasks);events=[];done=set()
    if len({t.task_id for t in pending})!=len(pending):raise ValueError("DUPLICATE_TASK_ID")
    if not isinstance(outcomes,dict):raise ValueError("OUTCOME_MAP_REQUIRED")
    for tick in range(max_ticks):
        if not pending:break
        r=plan(pending,workers,running=[],max_workers=3,max_heavy=3)
        if r["status"]!="PLAN_ONLY":return {"status":"BLOCKED","events":events,"reason":r.get("reason")}
        if not r["assignments"]:return {"status":"BLOCKED","events":events,"pending":[t.task_id for t in pending]}
        for a in r["assignments"]:
            task_id=a["task_id"]
            if task_id in done:raise ValueError("DUPLICATE_EXECUTION")
            outcome=outcomes.get(task_id)
            if outcome not in ("PASS","BLOCKED","FAIL"):raise ValueError("MISSING_SYNTHETIC_OUTCOME")
            state="PROPOSED"
            for nxt,evidence in [
              ("ADMISSION_PENDING",{}),
              ("ADMITTED",{"admission_id":"sim","worker_id":a["worker_id"]}),
              ("LEASED",{"lease_id":"sim","fencing_epoch":1}),
              ("RUNNING",{"pid":tick+1,"start_utc":"SIMULATED"}),
              ("VALIDATING",{"exit_code":0 if outcome=="PASS" else 1,"result_sha256":"sim"}),
              (outcome,{"validation_sha256":"sim","checkpoint_sha256":"sim",
                        "reason":"SYNTHETIC_BLOCKER","process_tree_stopped":True})]:
                v=transition(state,nxt,dict(evidence,verified=True))
                if v["status"]!="ACCEPTED":raise ValueError("LIFECYCLE_REJECTED:"+str(v))
                state=nxt
            events.append({"tick":tick,"task_id":task_id,"project":a["project"],
                           "worker_id":a["worker_id"],"result":outcome,"simulated":True})
            done.add(task_id)
        pending=[t for t in pending if t.task_id not in done]
    return {"status":"SIMULATION_COMPLETE" if not pending else "TICK_LIMIT",
            "events":events,"pending":[t.task_id for t in pending],
            "native_execution":False,"leases_modified":False}
