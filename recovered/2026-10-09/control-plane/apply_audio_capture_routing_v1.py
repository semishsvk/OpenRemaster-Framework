import json,os
from pathlib import Path
root=Path(__file__).resolve().parent
cap=root/"capabilities.json"
d=json.loads(cap.read_text(encoding="utf-8-sig"))
for w in d["workers"]:
 if w["worker_id"]=="HomePC-GodotRuntimeWorker":
  for c in ("audio.process_loopback","runtime.capture.wgc"):
   if c not in w["capabilities"]:w["capabilities"].append(c)
  w["constraints"]["audio_capture_process_tree_only"]=True
 if w["worker_id"]=="HomePC-NativeWorker":
  for c in ("audio.process_loopback","runtime.capture.wgc"):
   if c in w["capabilities"]:w["capabilities"].remove(c)
  w["constraints"]["interactive_fidelity_slots"]=0
tmp=cap.with_suffix(".json.audiotmp")
tmp.write_text(json.dumps(d,indent=2),encoding="utf-8")
os.replace(tmp,cap)
schema=root/"schemas"/"orch-k003-job.schema.json"
s=json.loads(schema.read_text(encoding="utf-8-sig"))
e=s["properties"]["execution"]["properties"]
e["audio_duration_ms"]={"type":"integer","minimum":250,"maximum":15000}
e["capture_backend"]={"const":"windows_graphics_capture"}
tmp=schema.with_suffix(".json.audiotmp")
tmp.write_text(json.dumps(s,indent=2),encoding="utf-8")
os.replace(tmp,schema)
print(json.dumps({"status":"PASS","gui_worker":"HomePC-GodotRuntimeWorker","audio_capability":"audio.process_loopback","native_session_0_gui_capacity":0}))
