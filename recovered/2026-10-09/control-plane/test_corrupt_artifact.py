import json,tempfile
from pathlib import Path
from idempotency import reconcile
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"result.json"
 p.write_bytes(b"{corrupt")
 a=reconcile(p,"x"); assert a["action"]=="QUARANTINE" and a["reason"]=="INVALID_RESULT"
 p.write_text(json.dumps({"status":"PASS","exit_code":0,"operation_id":"other"}),encoding="utf-8")
 b=reconcile(p,"expected"); assert b["action"]=="QUARANTINE" and b["reason"]=="OPERATION_ID_MISMATCH"
 print(json.dumps({"schema":"CorruptArtifactCanary.v1","status":"PASS","invalid_json":a,"identity_mismatch":b}))
