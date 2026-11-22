from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
backup=root/"orchestrator"/"backups"/"fidelity-mouse-v5-prechange-20261009"
paths=["orchestrator/control-plane/fidelity_targeted_input_v1.py",
"orchestrator/control-plane/fidelity_runtime_worker_v1.py",
"orchestrator/control-plane/orch_k003.py",
"orchestrator/control-plane/capabilities.json",
"orchestrator/control-plane/schemas/orch-k003-job.schema.json"]
record=[]
for relative in paths:
 src=root/relative;out=backup/relative
 assert src.is_file(),relative
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():assert out.read_bytes()==src.read_bytes()
 else:out.write_bytes(src.read_bytes())
 record.append({"path":relative,"sha256":hashlib.sha256(src.read_bytes()).hexdigest()})
e=backup/"backup-manifest.json"
e.write_text(json.dumps({"schema":"FidelityMouseV5PrechangeBackup.v1","files":record},indent=2))
print(json.dumps({"status":"BACKED_UP","files":len(record),"path":str(e)}))
