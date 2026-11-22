import json,tempfile
from pathlib import Path
from validator import validate
from acceptance import accept
job={"execution":{"kind":"godot_runtime"},"validation":{"expected_exit_code":0}}
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"result.json"
 p.write_text(json.dumps({"status":"PASS","exit_code":7,"fingerprint":{"remote_desktop_capture_authority":True}}),encoding="utf-8")
 v=validate(job,p)
 a=accept(job,v)
 assert v["status"]=="FAIL"
 assert "EXIT_CODE_MISMATCH" in v["failures"]
 assert "GODOT_FINGERPRINT_MISSING" in v["failures"]
 assert "REMOTE_DESKTOP_AUTHORITY_INVALID" in v["failures"]
 assert a["status"]=="FAIL"
 print(json.dumps({"schema":"NegativeValidationCanary.v1","status":"PASS","validation":v,"acceptance":a}))
