from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
dest=R/"orchestrator"/"backups"/"seed-adapter-pre-v6-20261009"
dest.mkdir(parents=True,exist_ok=True)
files=["orchestrator/control-plane/fidelity_seed_saves_v1.py",
       "orchestrator/control-plane/test_readonly_save_seed_v5.py"]
records=[]
for name in files:
 source=R/name;out=dest/source.name
 data=source.read_bytes()
 if out.exists():assert out.read_bytes()==data
 else:out.write_bytes(data)
 records.append({"path":name,"sha256":hashlib.sha256(data).hexdigest()})
(dest/"backup-manifest.json").write_text(json.dumps({"files":records},indent=2))
print(json.dumps({"status":"SOURCE_PRE_CHANGE_BACKUP_COMPLETE","files":records}))
