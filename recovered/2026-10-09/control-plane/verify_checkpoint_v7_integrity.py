"""Fresh independent rehydration contract audit for sealed v7 manifest.
Reads hashed artifact/evidence files, rechecks pinned source/registry. No game or GUI launch.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
R=Path(__file__).resolve().parents[2]
checkpoint=R/"runtime-test"/"results"/"fidelity-runtime-isolation-checkpoint-20261009-v7.json"
data=json.loads(checkpoint.read_text(encoding="utf-8-sig"))
assert data["schema"]=="OpenRemaster.FidelityRuntimeIsolationCheckpoint.v7"
assert data["status"].endswith("FIDELITY_HOLD")
assert data["current_regression_tests"]["count"]==27

def hash_bytes(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as stream:
  for b in iter(lambda:stream.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
verified=[]
drift=[]
missing=[]
for category in ("artifacts","evidence"):
 for x in data[category]:
  file=R/x["path"]
  if not file.is_file():
   missing.append(str(file));continue
  actual=hash_bytes(file)
  if actual!=x["sha256"]:
   drift.append({"file":str(file),"expected":x["sha256"],"actual":actual})
  else:verified.append(str(file))
source=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
pinned_ok=hash_bytes(source)==data["openzork"]["pinned_save_sha256"]
phase=R/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
phase_ok=hash_bytes(phase)==data["framework"]["frozen_phase1_policy_sha256"]
state="PASS" if not drift and not missing and pinned_ok and phase_ok else "DRIFT_OR_PROVENANCE_HOLD"
out={
 "schema":"OpenRemaster.FidelityIsolationCheckpointV7Integrity.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":state,"checkpoint_path":str(checkpoint),
 "checkpoint_sha256":hash_bytes(checkpoint),
 "verified_items":len(verified),
 "expected_items":len(data["artifacts"])+len(data["evidence"]),
 "missing_files":missing,
 "hash_drift":drift,
 "pinned_save_exact":pinned_ok,
 "phase1_policy_exact":phase_ok,
 "fidelity_verified":False}
target=R/"runtime-test"/"results"/"fidelity-runtime-isolation-v7-independent-integrity-20261009.json"
if target.exists():raise RuntimeError("V7_INTEGRITY_RESULT_ALREADY_EXISTS")
target.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":state,"verified":len(verified),"expected":out["expected_items"],
 "drift":len(drift),"missing":len(missing),"pinned":pinned_ok,
 "frozen_baseline":phase_ok,"checkpoint_sha256":out["checkpoint_sha256"],
 "evidence":str(target)},ensure_ascii=False))
raise SystemExit(0 if state=="PASS" else 1)
