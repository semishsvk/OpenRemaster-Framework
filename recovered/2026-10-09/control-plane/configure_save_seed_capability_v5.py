"""Enable source-read-only private ScummVM save seeding for interactive HomePC worker."""
import json,os
from pathlib import Path
base=Path(__file__).resolve().parent
cap=base/"capabilities.json"
obj=json.loads(cap.read_text(encoding="utf-8-sig"))
for w in obj["workers"]:
 if w["worker_id"]=="HomePC-GodotRuntimeWorker":
  if "runtime.saved_state_seed.copy" not in w["capabilities"]:
   w["capabilities"].append("runtime.saved_state_seed.copy")
  w["constraints"]["save_seed_source_read_only"]=True
  w["constraints"]["save_seed_project_isolation"]=True
 if w["worker_id"]=="HomePC-NativeWorker":
  assert "runtime.saved_state_seed.copy" not in w["capabilities"]
tmp=cap.with_suffix(".json.seed-tmp")
tmp.write_text(json.dumps(obj,indent=2),encoding="utf-8");os.replace(tmp,cap)
schema=base/"schemas"/"orch-k003-job.schema.json"
obj=json.loads(schema.read_text(encoding="utf-8-sig"))
obj["properties"]["execution"]["properties"]["seed_saves"]={
 "type":"array","minItems":1,"maxItems":4,
 "items":{"type":"object","required":["path","sha256"],"additionalProperties":False,
          "properties":{"path":{"type":"string"},"sha256":{"type":"string","minLength":64,"maxLength":64}}}
}
tmp=schema.with_suffix(".json.seed-tmp")
tmp.write_text(json.dumps(obj,indent=2),encoding="utf-8");os.replace(tmp,schema)
print(json.dumps({"schema":"OpenRemaster.ReadOnlySavedStateSeedContract.v1","status":"PASS",
"allowed_project":"OpenZork","worker":"HomePC-GodotRuntimeWorker",
"native_worker":"NOT_ROUTABLE_GUI","source_mutation":"FORBIDDEN"}))
