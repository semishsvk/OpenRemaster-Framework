"""Create a dedicated ORCH headless Godot asset import job for isolated staged OpenZork clone."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
stage=R/"work"/"OpenZork"/"staging"/"openzork-vb30-1058-godot-headless-20261009-r1"/"runtime"
assert stage.joinpath("project.godot").is_file()
rid="openzork-vb30-1058-private-import-20261009-r1"
jobfile=R/"runtime-test"/"jobs"/"fidelity-vb30-samepose"/(rid+".json")
assert not jobfile.exists()
p=stage/"project.godot"
j={"schema":"ORCH-K003.Job.v1","job_id":rid,
   "project":"OpenZork","task":"PrivateStagedGodotAssetImport",
   "inputs":[{"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}],
   "required_capabilities":["godot.headless"],
   "execution":{"kind":"godot_runtime","project_path":str(stage),
      "mode":"import","timeout_seconds":180,"args":[]},
   "validation":{"expected_exit_code":0}}
jobfile.write_text(json.dumps(j,indent=2),encoding="utf-8")
print(json.dumps({"status":"JOB_READY","job":str(jobfile),
                  "isolated_project":str(stage)}))
