"""Independent, read-only rehydration audit of canonical v8 checkpoint.
Does not modify old checkpoint or any original corpus/process/window.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2]
checkpoint=R/"runtime-test"/"results"/"fidelity-runtime-isolation-checkpoint-20261009-v8.json"
d=json.loads(checkpoint.read_text(encoding="utf-8-sig"))
assert d["schema"]=="OpenRemaster.FidelityRuntimeIsolationCheckpoint.v8"
assert d["v8_regression"]["passed"]==d["v8_regression"]["total"]==32
def digest(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as fp:
  for chunk in iter(lambda:fp.read(1024*1024),b""):
   h.update(chunk)
 return h.hexdigest()
checked=[];missing=[];drift=[]
for kind in ("artifacts","evidence"):
 for row in d[kind]:
  file=R/row["path"]
  if not file.is_file():
   missing.append({"kind":kind,"path":str(file)});continue
  sha=digest(file);size=file.stat().st_size
  if sha!=row["sha256"] or size!=row["bytes"]:
   drift.append({"kind":kind,"path":str(file),"expected_sha":row["sha256"],
      "actual_sha":sha,"expected_bytes":row["bytes"],"actual_bytes":size})
  else:checked.append(str(file))
old=R/"runtime-test"/"results"/"fidelity-runtime-isolation-checkpoint-20261009-v7.json"
old_ok=digest(old)==d["previous_checkpoint_sha256"]
frozen=R/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
frozen_ok=digest(frozen)==d["framework"]["frozen_policy_sha256"]
game=R/"source"/"Zork Nemesis"/"ZORKDOS.EXE"
game_ok=digest(game)==d["original_corpus_immutability"]["native_ZORKDOS_EXE_sha256"]
pinned=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
pinned_ok=digest(pinned)==d["original_corpus_immutability"]["pinned_VB30_saved_state_sha256"]
pass_ok=(not missing and not drift and len(checked)==45 and old_ok and frozen_ok and game_ok and pinned_ok)
r={"schema":"OpenRemaster.FidelityRuntimeV8IndependentIntegrityAudit.v1",
   "recorded_utc":datetime.now(timezone.utc).isoformat(),
   "status":"PASS" if pass_ok else "DRIFT_OR_REHYDRATION_HOLD",
   "checkpoint_sha256":digest(checkpoint),
   "items_verified":len(checked),"items_expected":len(d["artifacts"])+len(d["evidence"]),
   "missing":missing,"hash_or_size_drift":drift,
   "v7_unchanged":old_ok,"frozen_phase1_unchanged":frozen_ok,
   "original_ZORKDOS_sha256_valid":game_ok,"pinned_save_sha256_valid":pinned_ok,
   "native_original_first_courtyard":"SINGLE_RUN_TECHNICAL_PASS",
   "independent_native_run_repeatability":"NOT_VERIFIED",
   "original_vs_Godot_fidelity":"HOLD",
   "no_game_process_started_or_terminated":True}
target=R/"runtime-test"/"results"/"fidelity-runtime-isolation-v8-independent-integrity-20261009.json"
if target.exists():raise RuntimeError("V8_INTEGRITY_AUDIT_ALREADY_EXISTS")
target.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":r["status"],"verified":r["items_verified"],"expected":r["items_expected"],
 "checkpoint_sha256":r["checkpoint_sha256"],"missing":len(missing),"drift":len(drift),
 "v7":old_ok,"frozen_phase1":frozen_ok,"original_game":game_ok,"pinned":pinned_ok,
 "evidence":str(target)},ensure_ascii=False))
raise SystemExit(0 if pass_ok else 1)
