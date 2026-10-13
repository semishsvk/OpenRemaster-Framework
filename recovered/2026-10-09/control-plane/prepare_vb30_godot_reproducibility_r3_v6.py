"""Independent second headless Godot execution to test deterministic VB30@1058 output.
Reuses imported isolated staging sandbox; distinct job ID, output, immutable receipts.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
stage=R/"work"/"OpenZork"/"staging"/"openzork-vb30-1058-godot-headless-20261009-r1"/"runtime"
previous_script=stage/"scripts"/"openremaster_vb30_snapshot_r2.gd"
assert previous_script.is_file()
newid="openzork-vb30-1058-godot-headless-20261009-r3"
new_script=stage/"scripts"/"openremaster_vb30_snapshot_r3.gd"
assert not new_script.exists()
oldid="openzork-vb30-1058-godot-headless-20261009-r2"
source=previous_script.read_text(encoding="utf-8")
assert source.count(oldid)==1
new_script.write_text(source.replace(oldid,newid),encoding="utf-8")
old_job=R/"runtime-test"/"jobs"/"fidelity-vb30-samepose"/(oldid+".json")
j=json.loads(old_job.read_text(encoding="utf-8"))
j["job_id"]=newid
j["task"]="IndependentSecondHeadlessGodotVB30DeterminismRun"
j["execution"]["args"]=["--script","res://scripts/openremaster_vb30_snapshot_r3.gd"]
j["inputs"][-1]["path"]=str(new_script)
j["inputs"][-1]["sha256"]=hashlib.sha256(new_script.read_bytes()).hexdigest()
jobfile=old_job.with_name(newid+".json")
assert not jobfile.exists()
jobfile.write_text(json.dumps(j,indent=2),encoding="utf-8")
print(json.dumps({"status":"READY","job":str(jobfile),"run_id":newid,
 "source":str(stage),"script_sha256":j["inputs"][-1]["sha256"]}))
