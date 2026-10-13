"""Versioned snapshot before opt-in diagnostic admission; never overwrites an existing backup."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil
root=Path(__file__).resolve().parents[2]
targets=[
"orchestrator/control-plane/fidelity_runtime_worker_v1.py",
"orchestrator/control-plane/orch_k003.py",
"orchestrator/control-plane/validator.py",
"orchestrator/control-plane/capabilities.json",
"orchestrator/control-plane/schemas/orch-k003-job.schema.json",
"orchestrator/control-plane/fidelity-runtime-isolation.v1.json",
"orchestrator/native-worker/agent.py",
"orchestrator/control-plane/test_fidelity_runtime_orchestrator_v1.py"
]
base=root/"orchestrator"/"backups"/"fidelity-isolation-before-v3-20261009"
records=[]
for relative in targets:
 src=root/relative;dest=base/relative;dest.parent.mkdir(parents=True,exist_ok=True)
 assert src.is_file(), str(src)
 b=src.read_bytes()
 if dest.exists():
  assert dest.read_bytes()==b,f"Backup drift for {relative}"
 else:dest.write_bytes(b)
 records.append({"path":relative,"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)})
meta={"schema":"OpenRemaster.FidelityPreV3Backup.v1","created_at_utc":datetime.now(timezone.utc).isoformat(),"files":records}
p=base/"snapshot.json"
if not p.exists():p.write_text(json.dumps(meta,indent=2),encoding="utf-8")
print(json.dumps({"status":"BACKED_UP","files":len(records),"path":str(base)}))
