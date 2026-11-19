import json, tempfile
from pathlib import Path
from execution_journal import append_event, read_events

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"journal.jsonl"
    append_event(p,"canary","JOB_CREATED",lifecycle="CREATED")
    append_event(p,"canary","EXECUTION_STARTED",lifecycle="RUNNING",attempt_id="a1")
    append_event(p,"canary","EXECUTION_FINISHED",lifecycle="VALIDATING",attempt_id="a1")
    rows=read_events(p)
    assert [r["event"] for r in rows] == ["JOB_CREATED","EXECUTION_STARTED","EXECUTION_FINISHED"]
    assert rows[-1]["lifecycle"] == "VALIDATING"
    assert all(r["job_id"]=="canary" for r in rows)
    print(json.dumps({"schema":"ExecutionJournalCanary.v1","status":"PASS","events":len(rows)}))
