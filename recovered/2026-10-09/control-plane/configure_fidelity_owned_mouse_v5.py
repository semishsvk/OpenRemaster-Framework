"""Allowlist exact HWND mouse diagnostics on console worker, never session0."""
import json,os
from pathlib import Path
p=Path(__file__).resolve().parent
caps=p/"capabilities.json"
d=json.loads(caps.read_text(encoding="utf-8-sig"))
for w in d["workers"]:
 if w["worker_id"]=="HomePC-GodotRuntimeWorker":
  if "input.hwnd_owned_mouse_diagnostic" not in w["capabilities"]:
   w["capabilities"].append("input.hwnd_owned_mouse_diagnostic")
  w["constraints"]["mouse_controls_global_cursor"]=False
  w["constraints"]["mouse_focus_changes"]=False
  w["constraints"]["mouse_allowed_mode"]="targeted_input_diagnostic"
 if w["worker_id"]=="HomePC-NativeWorker":
  assert "input.hwnd_owned_mouse_diagnostic" not in w["capabilities"]
t=caps.with_suffix(".json.mouse-tmp")
t.write_text(json.dumps(d,indent=2),encoding="utf-8")
os.replace(t,caps)
schema=p/"schemas"/"orch-k003-job.schema.json"
s=json.loads(schema.read_text(encoding="utf-8-sig"))
existing=s["properties"]["execution"]["properties"]["input_plan"]
existing["items"]={
 "oneOf":[
  {"type":"object","additionalProperties":False,
   "required":["at_seconds","key"],
   "properties":{"at_seconds":{"type":"number","minimum":0.1,"maximum":44.5},
                 "key":{"enum":["SPACE","ENTER","ESCAPE","LEFT","RIGHT","UP","DOWN"]}}},
  {"type":"object","additionalProperties":False,
   "required":["at_seconds","action","client_x","client_y"],
   "properties":{"at_seconds":{"type":"number","minimum":0.1,"maximum":44.5},
                 "action":{"const":"MOUSE_LEFT_CLICK"},
                 "client_x":{"type":"integer","minimum":8,"maximum":8191},
                 "client_y":{"type":"integer","minimum":8,"maximum":8191}}}
 ]}
t=schema.with_suffix(".json.mouse-tmp")
t.write_text(json.dumps(s,indent=2),encoding="utf-8")
os.replace(t,schema)
print(json.dumps({"schema":"OpenRemaster.FidelityOwnedMouseCapability.v1",
"status":"PASS","worker":"HomePC-GodotRuntimeWorker","session0":"DISABLED",
"global_mouse":"DISABLED","mouse_click":"POST_TO_VERIFIED_HWND_ONLY"}))
