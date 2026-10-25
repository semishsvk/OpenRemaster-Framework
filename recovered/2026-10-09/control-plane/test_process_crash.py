import json, subprocess, sys, tempfile, time
from pathlib import Path
from recovery import project
from leases import inspect, acquire
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/"crash"
 p=subprocess.Popen([sys.executable,str(ROOT/"crash_child.py"),str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 line=p.stdout.readline().strip()
 assert line=="READY"
 p.kill(); p.wait(timeout=5)
 state=project(root/"execution-journal.jsonl")
 assert state["state"]=="INTERRUPTED" and state["recoverable"]
 time.sleep(2.2)
 assert inspect(root/"worker-lease.json")["status"]=="EXPIRED"
 takeover=acquire(root/"worker-lease.json","crash-canary","synthetic-worker","attempt-2",60)
 assert takeover["status"]=="ACQUIRED"
 print(json.dumps({"schema":"ProcessCrashCanary.v1","status":"PASS","recovery":state,"takeover_attempt":"attempt-2"}))
