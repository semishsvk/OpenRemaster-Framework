import json,os
from pathlib import Path
root=Path(__file__).resolve().parent
p=root/"capabilities.json";r=json.loads(p.read_text(encoding="utf-8-sig"))
for w in r["workers"]:
 if w["worker_id"]=="HomePC-GodotRuntimeWorker":
  if "runtime.passive_capture_diagnostic" not in w["capabilities"]:
   w["capabilities"].append("runtime.passive_capture_diagnostic")
  w["constraints"]["passive_capture_only_not_fidelity"]="YES"
 if w["worker_id"]=="HomePC-NativeWorker":
  assert "runtime.fidelity_isolated" not in w["capabilities"]
  assert "runtime.passive_capture_diagnostic" not in w["capabilities"]
t=p.with_suffix(".json.passive-tmp")
t.write_text(json.dumps(r,indent=2),encoding="utf-8");os.replace(t,p)
p=root/"schemas"/"orch-k003-job.schema.json"
r=json.loads(p.read_text(encoding="utf-8-sig"))
r["properties"]["execution"]["properties"]["capture_mode"]={"enum":["strict_fidelity","passive_diagnostic"]}
t=p.with_suffix(".json.passive-tmp")
t.write_text(json.dumps(r,indent=2),encoding="utf-8");os.replace(t,p)
print(json.dumps({"status":"PASS","passive_mode":"EXPLICIT_CAPABILITY_OPT_IN","strict_fidelity_mode":"UNCHANGED","gui_slots":1,"worker":"HomePC-GodotRuntimeWorker"}))
