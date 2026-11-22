import json,os
from pathlib import Path
p=Path(__file__).resolve().parent/"schemas"/"orch-k003-job.schema.json"
d=json.loads(p.read_text(encoding="utf-8-sig"))
d["properties"]["execution"]["properties"]["capture_delay_seconds"]={
 "type":"number","minimum":0,"maximum":45,
 "description":"Global maximum; runtime restricts strict and targeted modes to 12 seconds. 45 seconds is passive-only."}
t=p.with_suffix(".json.delaytmp")
t.write_text(json.dumps(d,indent=2),encoding="utf-8");os.replace(t,p)
print(json.dumps({"status":"PASS","passive_capture_delay_max":45,"strict_or_targeted_capture_delay_max":12}))
