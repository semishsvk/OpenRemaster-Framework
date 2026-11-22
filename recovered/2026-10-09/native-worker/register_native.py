import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
cp=root.parent/"control-plane"
caps=json.loads((cp/"capabilities.json").read_text(encoding="utf-8"))
native={"worker_id":"HomePC-NativeWorker","adapter":"NativeLocalQueue","enabled":True,"capabilities":["filesystem.read","filesystem.write_workspace","process.exec","python.exec","godot.4.7.2","godot.headless","runtime.replay","runtime.local_capture"],"constraints":{"source_corpus_read_only":True,"remote_desktop_stream_fidelity_authority":False}}
if not any(w["worker_id"]==native["worker_id"] for w in caps["workers"]):caps["workers"].append(native)
comm=json.loads((cp/"worker-commissioning.json").read_text(encoding="utf-8"))
comm["workers"][native["worker_id"]]={"status":"LOCAL_E2E_PASS","routable":False,"acl_boundary":"PENDING_DEDICATED_IDENTITY","production_canary":"native-worker-azrael-smoke-20261008","production_canary_status":"PASS"}
(cp/"capabilities.json").write_text(json.dumps(caps,indent=2),encoding="utf-8")
(cp/"worker-commissioning.json").write_text(json.dumps(comm,indent=2),encoding="utf-8")
print(json.dumps({"native_worker_registered":True,"routable":False,"reason":"DEDICATED_IDENTITY_AND_TRANSPORT_PENDING"}))
