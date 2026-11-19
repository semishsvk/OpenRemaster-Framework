import json,hashlib,datetime
from pathlib import Path
root=Path(r"F:\Remaster Framework")
m=root/"work/OpenAzrael/REHYDRATION_MANIFEST_V251.json"
r=root/"runtime-test/results/orch-k003-openazrael-kg001-001/control-receipt.json"
rr=root/"runtime-test/results/orch-k003-openazrael-kg001-001/result.json"
def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()
md=json.loads(m.read_text(encoding="utf-8")); rd=json.loads(r.read_text(encoding="utf-8")); runtime=json.loads(rr.read_text(encoding="utf-8"))
out={"schema":"DurableCheckpointAttestation.v1","project":"OpenAzrael","checkpoint":"candidate-v251-local-baseline","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"PASS" if rd.get("status")=="PASS" and runtime.get("status")=="PASS" else "FAIL","rehydration":{"manifest":str(m),"manifest_sha256":h(m),"tree_sha256":md["tree_sha256"],"file_count":md["file_count"],"restore_recipe":md["restore_recipe"]},"smoke":{"control_receipt":str(r),"control_receipt_sha256":h(r),"runtime_result":str(rr),"runtime_result_sha256":h(rr),"status":runtime.get("status"),"exit_code":runtime.get("exit_code")},"resulting_fingerprint":{"tree_sha256":md["tree_sha256"],"godot_sha256":runtime["fingerprint"]["godot_sha256"],"project_godot_sha256":runtime["fingerprint"]["project_godot_sha256"]},"claim_scope":"durable local execution checkpoint; does not claim original-runtime visual fidelity"}
q=root/"runtime-test/results/orch-k003-openazrael-kg001-001/durable-checkpoint-attestation.json";q.write_text(json.dumps(out,indent=2),encoding="utf-8");print(json.dumps(out,indent=2))
