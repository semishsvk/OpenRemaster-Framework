"""Independent actual Godot engine hotspot transition replay audit, private frame outputs.
Does not claim original runtime or player input/fidelity validation.
"""
from pathlib import Path
import json,hashlib
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parents[2]
rid="openzork-vb30-scene-hotspot-headless-20261009-r1"
base=R/"runtime-test"/"results"/rid
p=base/"scene-hotspot-replay-plan.json"
plan=json.loads(p.read_text(encoding="utf-8"))
r=json.loads((base/"control-receipt.json").read_text(encoding="utf-8"))
v=json.loads((base/"validation-result.json").read_text(encoding="utf-8"))
out=(base/"stdout.log").read_text(encoding="utf-8")
err=(base/"stderr.log").read_text(encoding="utf-8")
assert r["status"]==v["status"]=="PASS" and r["acceptance_status"]=="PASS"
assert "PANA_PROJECTED_HOTSPOT_E2E=PASS" in out
assert "TRANSITION VB20@1058 puzzle=17367" in out
assert "TRANSITION VB30@364 puzzle=17362" in out
assert not err.strip(),err
h=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
fr=[base/("VB30_HOTSPOT_REPLAY_%02d.png"%i) for i in range(3)]
assert all(f.is_file() for f in fr)
imgs=[]
info=[]
for i,f in enumerate(fr):
 with Image.open(f) as im:
  a=np.array(im.convert("RGB"),dtype=np.uint8)
  assert a.shape==(320,512,3),a.shape
  imgs.append(a)
 info.append({"index":i,"scene":["VB30","VB20","VB30"][i],
   "view":[1058,1058,364][i],"sha256":h(f),"bytes":f.stat().st_size})
previous=R/"runtime-test"/"results"/"openzork-vb30-1058-godot-headless-20261009-r2"/"engine-vb30-1058.png"
assert fr[0].read_bytes()==previous.read_bytes()
assert not np.array_equal(imgs[0],imgs[1])
assert not np.array_equal(imgs[0],imgs[2])
orig=R/"work"/"OpenZork"/"runtime"/"scripts"/"capture_helper.gd"
assert h(orig)==plan["original_capture_helper_sha256"],"shared evidence helper was altered"
src=R/"work"/"OpenZork"/"runtime"/"scripts"/"interactive_runtime.gd"
assert h(src)==plan["source_runtime_original_sha256"]
record={
 "schema":"OpenZork.VB30VB20HeadlessRuntimeHotspotReplay.v1",
 "status":"ACTUAL_GODOT_RUNTIME_STRUCTURAL_HOTSPOT_REPLAY_PASS_FIDELITY_HOLD",
 "engine_version":"4.7.2.stable",
 "job_id":rid,
 "runtime_receipt_sha256":h(base/"control-receipt.json"),
 "runtime_log_sha256":h(base/"stdout.log"),
 "scene_transitions":[
    {"from":"VB30@1058","to":"VB20@1058","puzzle_slot":17367},
    {"from":"VB20@364","to":"VB30@364","puzzle_slot":17362}
 ],
 "actual_engine_frame_sha256":info,
 "first_frame_exact_matches_independent_godot_run":True,
 "original_source_gd_files_unchanged":True,
 "graph_hotspot_puzzle_execution":"PASS",
 "external_mouse_key_input_replay":"NOT_RUN",
 "original_ScummVM_or_DOS_state_transition_match":"NOT_TESTED",
 "gameplay_playable":"NOT_VERIFIED",
 "fidelity_verified":False}
dest=base/"hotspot-runtime-replay-evidence.json"
dest.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"frame_hashes":[x["sha256"] for x in info],
 "first_frame_matches_reference":True,
 "transition":record["scene_transitions"],"evidence":str(dest)},ensure_ascii=False))
