"""Stage original OpenZork Godot assets/code into private workspace.
Creates read-only-origin copy plus scoped headless render SceneTree script. No user GUI.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,shutil,hashlib,os
R=Path(__file__).resolve().parents[2]
source=R/"work"/"OpenZork"/"runtime"
rid="openzork-vb30-1058-godot-headless-20261009-r1"
stage=R/"work"/"OpenZork"/"staging"/rid/"runtime"
result=R/"runtime-test"/"results"/rid
if stage.exists() or (result/"engine-vb30-1058.png").exists():
 raise RuntimeError("STAGED_RUN_ALREADY_EXISTS_WILL_NOT_OVERWRITE")
stage.parent.mkdir(parents=True,exist_ok=True)
result.mkdir(parents=True,exist_ok=True)
shutil.copytree(source,stage,ignore=shutil.ignore_patterns(".godot"))
render_script=stage/"scripts"/"openremaster_vb30_snapshot.gd"
png=(result/"engine-vb30-1058.png").as_posix()
gd=f'''extends SceneTree

func _initialize() -> void:
    call_deferred("_produce_snapshot")

func _produce_snapshot() -> void:
    var scene_ref = load("res://main.tscn")
    if scene_ref == null:
        printerr("OPENREMASTER_MISSING_MAIN_SCENE")
        quit(10)
        return
    var node = scene_ref.instantiate()
    root.add_child(node)
    await process_frame
    var scene_name = str(node.get("scene_id"))
    var view = int(node.get("view_pos"))
    if scene_name != "VB30" or view != 1058:
        printerr("OPENREMASTER_POSE_MISMATCH ",scene_name,"@",view)
        quit(11)
        return
    var frame = node.get("latest_frame")
    if frame == null or frame.get_width() != 512 or frame.get_height() != 320:
        printerr("OPENREMASTER_IMAGE_INVALID")
        quit(12)
        return
    var target = "{png}"
    var code = frame.save_png(target)
    if code != OK:
        printerr("OPENREMASTER_CAPTURE_WRITE_FAILURE ",code)
        quit(13)
        return
    print("OPENREMASTER_VB30_1058_GODOT_RUNTIME_CAPTURE_PASS ",target)
    quit(0)
'''
render_script.write_text(gd,encoding="utf-8")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original=[
 "project.godot","main.tscn","scripts/interactive_runtime.gd",
 "scripts/hd_projection.gd","assets/VB30S11C.ppm",
 "slice_ir_v2.json"
]
records=[]
for name in original:
 a=source/name;b=stage/name
 assert a.is_file() and b.is_file() and a.read_bytes()==b.read_bytes()
 records.append({"path":name,"origin_sha256":sha(a),"stage_sha256":sha(b)})
pose=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"/"vb30-save-scene-pose-and-decoder-v6.json"
p=json.loads(pose.read_text())
assert p["location_key"]=="VB30" and p["view_coordinate"]==1058
job={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"IsolatedGodotActualRuntimeVB30SavePoseFrame",
 "inputs":[{"path":str(source/"scripts"/"interactive_runtime.gd"),"sha256":sha(source/"scripts"/"interactive_runtime.gd")},
           {"path":str(source/"assets"/"VB30S11C.ppm"),"sha256":sha(source/"assets"/"VB30S11C.ppm")},
           {"path":str(pose),"sha256":sha(pose)}],
 "required_capabilities":["godot.headless"],
 "execution":{"kind":"godot_runtime","project_path":str(stage),
              "mode":"headless","args":["--script","res://scripts/openremaster_vb30_snapshot.gd"],
              "timeout_seconds":210},
 "validation":{"expected_exit_code":0},
 "acceptance":{"require_validation_pass":True}
}
jobs=R/"runtime-test"/"jobs"/"fidelity-vb30-samepose"
jobs.mkdir(parents=True,exist_ok=True)
jobfile=jobs/(rid+".json")
if jobfile.exists():raise RuntimeError("JOB_ALREADY_EXISTS")
jobfile.write_text(json.dumps(job,indent=2),encoding="utf-8")
receipt={"schema":"OpenZork.IsolatedGodotVB30RenderPlan.v1",
"status":"STAGED_UNEXECUTED",
"run_id":rid,"source_read_only":True,
"original_godot_project":str(source),"isolated_project":str(stage),
"project_files_copied":len(list(stage.rglob("*"))),
"hash_verified_provenance":records,
"godot_renderer":"interactive_runtime.gd latest_frame 512x320 CPU projection inside ACTUAL GODOT",
"source_camera_pose":"VB30@1058","output":str(result/"engine-vb30-1058.png"),
"command_kind":"ORCH_K003_GODOT_HEADLESS","job":str(jobfile),
"script_sha256":sha(render_script),
"game_fidelity":"NOT_YET_TESTED"}
receipt_file=result/"render-staging-plan.json"
receipt_file.write_text(json.dumps(receipt,indent=2),encoding="utf-8")
print(json.dumps({"status":"STAGED_UNEXECUTED","run_id":rid,
 "stage":str(stage),"source_files_verified":len(records),
 "job":str(jobfile),"out":receipt["output"],
 "receipt":str(receipt_file)},ensure_ascii=False))
