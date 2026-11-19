import json,tempfile
from pathlib import Path
from idempotency import operation_id,reconcile
job={"job_id":"x","project":"P","task":"T","execution":{"kind":"godot_runtime","project_path":"X"},"required_capabilities":["a"]}
op=operation_id(job)
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"result.json"
 assert reconcile(p,op)["action"]=="EXECUTE"
 p.write_text(json.dumps({"status":"PASS","exit_code":0,"operation_id":op}),encoding="utf-8")
 assert reconcile(p,op)["action"]=="REUSE_RESULT"
 assert reconcile(p,"wrong")["action"]=="QUARANTINE"
 print(json.dumps({"schema":"IdempotencyCanary.v1","status":"PASS","operation_id":op}))
