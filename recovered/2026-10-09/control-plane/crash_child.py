import sys,time
from pathlib import Path
from execution_journal import append_event
from leases import acquire
root=Path(sys.argv[1]); root.mkdir(parents=True,exist_ok=True)
j=root/"execution-journal.jsonl"; l=root/"worker-lease.json"
append_event(j,"crash-canary","JOB_CREATED",lifecycle="CREATED")
x=acquire(l,"crash-canary","synthetic-worker","attempt-1",ttl_seconds=2)
append_event(j,"crash-canary","LEASE_ACQUIRED",lifecycle="PREPARING",attempt_id="attempt-1")
append_event(j,"crash-canary","EXECUTION_STARTED",lifecycle="RUNNING",attempt_id="attempt-1")
print("READY",flush=True)
time.sleep(60)
