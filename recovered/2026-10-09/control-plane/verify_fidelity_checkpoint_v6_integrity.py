"""Read-only independent rehydration audit for v6 checkpoint.
Never change evidence, run game, or terminate a process. Hashes decide integrity.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2]
cp=R/"runtime-test"/"results"/"fidelity-runtime-isolation-checkpoint-20261009-v6.json"
data=json.loads(cp.read_text(encoding="utf-8-sig"))
assert data.get("schema")=="OpenRemaster.FidelityRuntimeIsolationCheckpoint.v6"
def sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
missing=[]
drift=[]
ok=0
for category in ("artifacts","evidence"):
 for row in data.get(category,[]):
  path=R/row["path"] if category=="artifacts" else Path(row["path"])
  if not path.is_file():
   missing.append({"kind":category,"path":str(path)})
   continue
  actual=sha(path)
  if actual!=row["sha256"]:
   drift.append({"kind":category,"path":str(path),"expected":row["sha256"],"actual":actual})
  else:ok+=1
src=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
saved_src=R/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"saves"/"znemesis.000"
frozen=R/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
expected_source=data["source_immutability"]["pinned_golden_save_sha256"]
assert src.is_file() and sha(src)==expected_source
assert sha(frozen)==data["source_immutability"]["Phase1_frozen_policy_sha256"]
report={
 "schema":"OpenRemaster.FidelityCheckpointV6RehydrationAudit.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "checkpoint_path":str(cp),
 "checkpoint_sha256":sha(cp),
 "status":"PASS" if not missing and not drift else "DRIFT_DETECTED_REHYDRATION_HOLD",
 "items_verified":ok,"items_missing":missing,"items_drifted":drift,
 "pinned_golden_save_hash_verified":True,
 "mutable_legacy_save_authority":False,
 "mutable_legacy_save_current_sha256":sha(saved_src) if saved_src.is_file() else None,
 "frozen_policy_verified":True,
 "fidelity_promotion":"NOT_AUTHORIZED"}
out=R/"runtime-test"/"results"/"fidelity-checkpoint-v6-integrity-audit-20261009.json"
if out.exists():raise RuntimeError("AUDIT_RESULT_ALREADY_EXISTS_NO_OVERWRITE")
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"checkpoint_sha256":report["checkpoint_sha256"],
 "items_verified":ok,"missing":len(missing),"drift":len(drift),
 "drift_details":drift[:10],"pinned_save":True,
 "report":str(out)},ensure_ascii=False))
