"""Bind a new unique Godot headless capture to the imported staged project.
No authoritative corpus write; old failed attempt r1 remains append-only evidence.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
stage=R/"work"/"OpenZork"/"staging"/"openzork-vb30-1058-godot-headless-20261009-r1"/"runtime"
prior=stage/"scripts"/"openremaster_vb30_snapshot.gd"
assert stage.joinpath(".godot").is_dir(),"Private import not completed"
assert prior.is_file()
rid="openzork-vb30-1058-godot-headless-20261009-r2"
output=R/"runtime-test"/"results"/rid/"engine-vb30-1058.png"
assert not output.exists()
output.parent.mkdir(parents=True,exist_ok=True)
script=stage/"scripts"/"openremaster_vb30_snapshot_r2.gd"
assert not script.exists()
old_text=prior.read_text(encoding="utf-8")
previous=str(R/"runtime-test"/"results"/"openzork-vb30-1058-godot-headless-20261009-r1"/"engine-vb30-1058.png").replace("\\","/")
new=str(output).replace("\\","/")
assert old_text.count(previous)==1
script.write_text(old_text.replace(previous,new),encoding="utf-8")
jobfile=R/"runtime-test"/"jobs"/"fidelity-vb30-samepose"/(rid+".json")
assert not jobfile.exists()
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"PrivateImportedGodotVB30SavePoseActualRenderer",
 "inputs":[{"path":str(stage/"project.godot"),"sha256":h(stage/"project.godot")},
           {"path":str(stage/"assets"/"VB30S11C.ppm"),"sha256":h(stage/"assets"/"VB30S11C.ppm")},
           {"path":str(script),"sha256":h(script)}],
 "required_capabilities":["godot.headless"],
 "execution":{"kind":"godot_runtime","project_path":str(stage),
  "mode":"headless","args":["--script","res://scripts/openremaster_vb30_snapshot_r2.gd"],
  "timeout_seconds":180},
 "validation":{"expected_exit_code":0}}
jobfile.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"READY","run_id":rid,"staged_project":str(stage),
 "render_script_hash":h(script),"output":str(output),"job":str(jobfile)}))
