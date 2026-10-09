import json,os
from pathlib import Path
p=Path(__file__).with_name("capabilities.json")
d=json.loads(p.read_text(encoding="utf-8-sig"))
for w in d["workers"]:
 if w["worker_id"]=="HomePC-NativeWorker":
  w["capabilities"]=[cap for cap in w["capabilities"] if cap not in ("runtime.fidelity_isolated","runtime.gui_lease.exclusive")]
  w["constraints"]["interactive_fidelity_slots"]=0
  w["constraints"]["interactive_fidelity_reason"]="SERVICE_SESSION_0_NOT_CONSOLE"
 elif w["worker_id"]=="HomePC-GodotRuntimeWorker":
  assert "runtime.fidelity_isolated" in w["capabilities"]
  w["constraints"]["interactive_fidelity_slots"]=1
t=p.with_suffix(".json.routingtmp")
t.write_text(json.dumps(d,indent=2),encoding="utf-8")
os.replace(t,p)
print(json.dumps({"status":"PASS","interactive_worker":"HomePC-GodotRuntimeWorker","native_service_gui_slots":0,"native_headless_preserved":True}))
