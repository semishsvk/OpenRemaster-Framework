"""Immutable pre-v7 snapshots of supervised runtime admission implementation."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
files=[
 "orchestrator/control-plane/fidelity_runtime_worker_v1.py",
 "orchestrator/control-plane/fidelity_runtime_isolation_v1.py",
 "orchestrator/control-plane/validator.py",
 "orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py"
]
backup=R/"orchestrator"/"backups"/"fidelity-target-binding-before-v7-20261009"
items=[]
for rel in files:
 path=R/rel
 dest=backup/rel
 dest.parent.mkdir(parents=True,exist_ok=True)
 data=path.read_bytes()
 if dest.exists() and dest.read_bytes()!=data:raise RuntimeError("BACKUP_DRIFT:"+rel)
 if not dest.exists():dest.write_bytes(data)
 items.append({"original":rel,"backup":str(dest),"sha256":hashlib.sha256(data).hexdigest()})
rec=backup/"manifest.json"
if not rec.exists():rec.write_text(json.dumps({"schema":"OpenRemaster.TargetBindingV7PreChangeBackup.v1","files":items},indent=2),encoding="utf-8")
print(json.dumps({"status":"BACKED_UP","files":len(items),"path":str(backup)},ensure_ascii=False))
