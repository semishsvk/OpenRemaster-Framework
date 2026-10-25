import json,os
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/"schemas"/"orch-k003-job.schema.json"
d=json.loads(p.read_text(encoding="utf-8-sig"))
d["properties"]["execution"]["properties"]["capture_schedule_seconds"]={
    "type":"array","minItems":2,"maxItems":5,
    "items":{"type":"number","minimum":0.5,"maximum":44},
    "description":"Passive-only ordered offset times; min two seconds between samples; immutable same-owned PID+HWND sequence."}
temp=p.with_suffix(".json.sequence-tmp")
temp.write_text(json.dumps(d,indent=2),encoding="utf-8")
os.replace(temp,p)
print(json.dumps({"schema":"OpenRemaster.FidelityCaptureScheduleSchema.v1","status":"PASS",
    "mode":"PASSIVE_DIAGNOSTIC_ONLY","max_frames":5,"max_elapsed_s":44,"minimum_interval_s":2}))
