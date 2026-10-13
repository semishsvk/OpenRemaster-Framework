"""Backup exact pre-v6 ORCH-K003 before adding interpreter GUI guard."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[2]
source=root/"orchestrator"/"control-plane"/"orch_k003.py"
dest=root/"orchestrator"/"backups"/"legacy-gui-executable-admission-pre-v6-20261009"
dest.mkdir(parents=True,exist_ok=True)
target=dest/"orch_k003.py"
data=source.read_bytes()
if target.exists():assert target.read_bytes()==data
else:target.write_bytes(data)
digest=hashlib.sha256(data).hexdigest()
(dest/"manifest.json").write_text(json.dumps({"original":str(source),"backup":str(target),"sha256":digest},indent=2))
print(json.dumps({"status":"BACKUP_VERIFIED","path":str(target),"sha256":digest}))
