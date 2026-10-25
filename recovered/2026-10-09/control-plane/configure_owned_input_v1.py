import json,os
from pathlib import Path
root=Path(__file__).resolve().parent
cap=root/"capabilities.json"
d=json.loads(cap.read_text(encoding="utf-8-sig"))
for w in d["workers"]:
 if w["worker_id"]=="HomePC-GodotRuntimeWorker":
  if "input.hwnd_owned_diagnostic" not in w["capabilities"]:
   w["capabilities"].append("input.hwnd_owned_diagnostic")
  w["constraints"]["hwnd_input_post_only_no_focus_switch"]=True
 if w["worker_id"]=="HomePC-NativeWorker":
  assert "runtime.fidelity_isolated" not in w["capabilities"]
  assert "input.hwnd_owned_diagnostic" not in w["capabilities"]
t=cap.with_suffix(".json.input-tmp");t.write_text(json.dumps(d,indent=2),encoding="utf-8");os.replace(t,cap)
schema=root/"schemas"/"orch-k003-job.schema.json"
s=json.loads(schema.read_text(encoding="utf-8-sig"))
e=s["properties"]["execution"]["properties"]
e["capture_mode"]["enum"]=["strict_fidelity","passive_diagnostic","targeted_input_diagnostic"]
e["input_plan"]={"type":"array","minItems":1,"maxItems":8,"items":{
 "type":"object","required":["at_seconds","key"],"additionalProperties":False,
 "properties":{"at_seconds":{"type":"number","minimum":0.1,"maximum":11.5},
               "key":{"enum":["SPACE","ENTER","ESCAPE","LEFT","RIGHT","UP","DOWN"]}}}}
t=schema.with_suffix(".json.input-tmp");t.write_text(json.dumps(s,indent=2),encoding="utf-8");os.replace(t,schema)
print(json.dumps({"status":"PASS","caps":["input.hwnd_owned_diagnostic"],"session0":"NO_GUI_INPUT","global_input":"FORBIDDEN"}))
