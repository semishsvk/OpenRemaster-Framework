import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
cp=root.parent/"control-plane"
evidence=root/"queue"/"done"/"dedicated-identity-evidence.json"
canary=root/"queue"/"done"/"dedicated-godot-canary-result.json"
assert json.loads(evidence.read_text())["status"]=="PASS"
assert json.loads(canary.read_text())["orchestrator_exit"]==0
caps=json.loads((cp/"capabilities.json").read_text())
comm=json.loads((cp/"worker-commissioning.json").read_text())
w=comm["workers"]["HomePC-NativeWorker"]
w.update(status="LOCAL_DEDICATED_E2E_PASS",routable=True,acl_boundary="DEDICATED_IDENTITY_CANARY_PASS",production_canary="native-dedicated-azrael-20261008")
(cp/"worker-commissioning.json").write_text(json.dumps(comm,indent=2))
print(json.dumps({"native_routable":True,"fallback_routable":comm["workers"]["HomePC-GodotRuntimeWorker"]["routable"]}))
