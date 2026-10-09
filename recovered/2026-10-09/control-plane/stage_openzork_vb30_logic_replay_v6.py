"""Private Godot self-test scene transition replay with output-path isolation.
No user GUI and no canonical source/evidence file writes. Reuses existing native Godot scripts.
"""
from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parents[2]
origin=R/"work"/"OpenZork"/"runtime"
prior=R/"work"/"OpenZork"/"staging"/"openzork-vb30-1058-godot-headless-20261009-r1"/"runtime"
rid="openzork-vb30-scene-hotspot-headless-20261009-r1"
stage=R/"work"/"OpenZork"/"staging"/rid/"runtime"
dest=R/"runtime-test"/"results"/rid
if stage.exists():raise RuntimeError("SCENE_REPLAY_STAGE_ALREADY_EXISTS_NO_OVERWRITE")
dest.mkdir(parents=True,exist_ok=True)
# Imported resource cache is copied only between private workspaces, never from canonical source.
shutil.copytree(prior,stage)
cap=stage/"scripts"/"capture_helper.gd"
old=cap.read_text(encoding="utf-8")
known="F:/Remaster Framework/work/OpenZork/evidence/FIDELITY_CANDIDATE_%02d.png"
new=str((dest/"VB30_HOTSPOT_REPLAY_%02d.png")).replace("\\","/")
assert old.count(known)==1,old
cap.write_text(old.replace(known,new),encoding="utf-8")
assert origin.joinpath("scripts/capture_helper.gd").read_text(encoding="utf-8")==old
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[
 ("engine_main",stage/"scripts"/"interactive_runtime.gd"),
 ("panorama_vb30",stage/"assets"/"VB30S11C.ppm"),
 ("panorama_vb20",stage/"assets"/"VB20S11C.ppm"),
 ("projection_hd",stage/"scripts"/"hd_projection.gd"),
 ("script_capture_scoped",cap)
]
job={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"HeadlessVB30ToVB20HotspotStructuralReplay",
 "inputs":[{"path":str(p),"sha256":h(p)} for _,p in inputs],
 "required_capabilities":["godot.headless"],
 "execution":{"kind":"godot_runtime","project_path":str(stage),
             "mode":"replay","args":["--","--self-test"],
             "timeout_seconds":180},
 "validation":{"expected_exit_code":0}
}
jobpath=R/"runtime-test"/"jobs"/"fidelity-vb30-samepose"/(rid+".json")
assert not jobpath.exists()
jobpath.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
report={
 "schema":"OpenZork.HeadlessSceneReplayStaging.v1","status":"STAGED_NOT_EXECUTED",
 "run_id":rid,"source_runtime_original_sha256":h(origin/"scripts"/"interactive_runtime.gd"),
 "private_runtime_source_sha256":h(stage/"scripts"/"interactive_runtime.gd"),
 "original_capture_helper_sha256":h(origin/"scripts"/"capture_helper.gd"),
 "private_output_capture_helper_sha256":h(cap),
 "original_source_modified":False,"original_evidence_modified":False,
 "private_outputs":[str(dest/("VB30_HOTSPOT_REPLAY_%02d.png"%i)) for i in range(3)],
 "job":str(jobpath),"stage":str(stage)
}
p=dest/"scene-hotspot-replay-plan.json"
p.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"run_id":rid,
"original_helper_untouched":report["original_evidence_modified"] is False,
"staged_output_only":True,"job":str(jobpath)},ensure_ascii=False))
