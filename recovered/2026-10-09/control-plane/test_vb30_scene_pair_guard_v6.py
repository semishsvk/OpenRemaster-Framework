"""Positive VB30@1058 pose from saved original and actual Godot, negative TA30 and altered view.
Artifacts are real existing local captures and explicit hashes; no processes launched.
"""
from pathlib import Path
import json,hashlib,copy
from fidelity_scene_pair_guard_v1 import attest_paired_scene,ScenePairError
R=Path(__file__).resolve().parents[2]
base=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
engine=R/"runtime-test"/"results"/"openzork-vb30-1058-godot-headless-20261009-r2"
pose=base/"vb30-save-scene-pose-and-decoder-v6.json"
pose_content=json.loads(pose.read_text(encoding="utf-8"))
assert pose_content["location_key"]=="VB30" and pose_content["view_coordinate"]==1058
outlog=engine/"stdout.log"
log=outlog.read_text(encoding="utf-8")
assert "OPENZORK_FIDELITY_CANDIDATE_READY VB30@1058" in log
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original={
 "game":"OpenZork","scene":"VB30","view":1058,"orientation_period":1440,
 "capture_path":str(base/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"),
 "capture_sha256":h(base/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"),
 "identity_provenance_path":str(pose),"identity_provenance_sha256":h(pose)}
candidate={
 "game":"OpenZork","scene":"VB30","view":1058,"orientation_period":1440,
 "capture_path":str(engine/"engine-vb30-1058.png"),
 "capture_sha256":h(engine/"engine-vb30-1058.png"),
 "identity_provenance_path":str(outlog),"identity_provenance_sha256":h(outlog)}
positive=attest_paired_scene(original,candidate)
assert positive["fidelity_verified"] is False
r30=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-R10-MASKED-DIFF-r30"/"R30_MASKED_ALIGNMENT_CHECKPOINT.json"
r29image=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-R10-PIXEL-FIDELITY-r29"/"GODOT_MATCHED_0_TA30_328.png"
assert r30.is_file() and r29image.is_file()
r30data=json.loads(r30.read_text(encoding="utf-8-sig"))
assert r30data["refined_first_scene"].startswith("TA30@")
negative=copy.deepcopy(candidate)
negative.update({"scene":"TA30","view":330,"capture_path":str(r29image),
                 "capture_sha256":h(r29image),
                 "identity_provenance_path":str(r30),
                 "identity_provenance_sha256":h(r30)})
cases=[]
def rejects(reason,other):
 try:attest_paired_scene(original,other)
 except ScenePairError as exc:
  assert exc.reason==reason,(exc.reason,reason)
  cases.append({"name":reason,"status":"BLOCKED"})
  return
 raise AssertionError("Fail-open scene pairing: "+reason)
rejects("PAIR_SCENE_MISMATCH",negative)
wrong=copy.deepcopy(candidate);wrong["view"]=330
rejects("PAIR_CAMERA_VIEW_MISMATCH",wrong)
wrong=copy.deepcopy(candidate);wrong["capture_sha256"]="0"*64
rejects("PAIR_EVIDENCE_HASH_MISMATCH",wrong)
wrong=copy.deepcopy(candidate);wrong["scene"]="UNKNOWN"
rejects("PAIR_SCENE_KEY_INVALID",wrong)
result={"schema":"OpenZork.VB30GoldenScenePairingGate.v1",
 "status":"SCENE_PAIR_TECHNICAL_PASS_NEGATIVE_MISMATCHES_BLOCKED",
 "scene_pose":positive,"positive_pair":dict(original=original,candidate=candidate),
 "negative_cases":cases,"R30_TA30_vb30_mismatch_proven":True,
 "real_godot_runtime_capture":True,
 "fidelity_attested":False}
dest=engine/"vb30-original-godot-scene-pair-guard.json"
dest.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],"positive_scene":"VB30@1058",
 "negative_cases":[c["name"] for c in cases],
 "hashes_verified":positive["hashes_verified"],"fidelity_attested":False,
 "evidence":str(dest)},ensure_ascii=False))
