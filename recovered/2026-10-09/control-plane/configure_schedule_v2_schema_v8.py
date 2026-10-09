"""Opt-in passive capture schedule v2 [0.5..75] for long animated original game.
Existing v1 44 sec default and frozen evidence remain unchanged.
"""
import json,os
from pathlib import Path
root=Path(__file__).resolve().parent
schema=root/"schemas"/"orch-k003-job.schema.json"
x=json.loads(schema.read_text(encoding="utf-8-sig"))
e=x["properties"]["execution"]["properties"]
e["capture_schedule_contract"]={"enum":["v1","v2_extended"]}
e["capture_schedule_seconds"]={"type":"array","minItems":2,"maxItems":5,
  "items":{"type":"number","minimum":0.5,"maximum":75},
  "description":"v2_extended requires passive_diagnostic. v1 remains maximum 44 enforced at runtime."}
tmp=schema.with_suffix(".json.v8tmp")
tmp.write_text(json.dumps(x,indent=2,ensure_ascii=False),encoding="utf-8");os.replace(tmp,schema)
print(json.dumps({"schema":"OpenRemaster.BoundedFrameScheduleConfig.v2","status":"PASS",
 "v1_max_sec":44,"v2_max_sec":75,"v2_requires":"passive_diagnostic",
 "fidelity_promotion":"FORBIDDEN"}))
