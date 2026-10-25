import json,tempfile
from pathlib import Path
from execution_journal import append_event
from recovery import project

with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"j.jsonl"
 append_event(p,"x","JOB_CREATED",lifecycle="CREATED")
 append_event(p,"x","WORKER_SELECTED",lifecycle="PREPARING")
 append_event(p,"x","EXECUTION_STARTED",lifecycle="RUNNING",attempt_id="a1")
 s=project(p)
 assert s["state"]=="INTERRUPTED" and s["recoverable"] is True
 assert s["reason"]=="EXECUTION_OUTCOME_UNKNOWN_RECONCILE_REQUIRED"
 print(json.dumps({"schema":"JournalRecoveryCanary.v1","status":"PASS","projection":s}))
