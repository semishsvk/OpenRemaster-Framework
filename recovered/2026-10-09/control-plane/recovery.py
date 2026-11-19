from execution_journal import read_events

TERMINAL={"JOB_COMPLETED":"COMPLETED","JOB_FAILED":"FAILED","JOB_BLOCKED":"BLOCKED"}

def project(path):
    rows=read_events(path)
    if not rows:
        return {"state":"UNKNOWN","recoverable":False,"events":0}
    last=rows[-1]["event"]
    if last in TERMINAL:
        return {"state":TERMINAL[last],"recoverable":False,"events":len(rows),"last_event":last}
    names=[r["event"] for r in rows]
    if "EXECUTION_STARTED" in names and "EXECUTION_FINISHED" not in names:
        return {"state":"INTERRUPTED","recoverable":True,"events":len(rows),"last_event":last,
                "reason":"EXECUTION_OUTCOME_UNKNOWN_RECONCILE_REQUIRED"}
    if "EXECUTION_FINISHED" in names and "VALIDATION_FINISHED" not in names:
        return {"state":"RECOVERING","recoverable":True,"events":len(rows),"last_event":last,
                "reason":"RESUME_VALIDATION"}
    if "VALIDATION_FINISHED" in names and "ACCEPTANCE_FINISHED" not in names:
        return {"state":"RECOVERING","recoverable":True,"events":len(rows),"last_event":last,
                "reason":"RESUME_ACCEPTANCE"}
    return {"state":"RECOVERING","recoverable":True,"events":len(rows),"last_event":last,
            "reason":"REPLAY_FROM_JOURNAL"}
