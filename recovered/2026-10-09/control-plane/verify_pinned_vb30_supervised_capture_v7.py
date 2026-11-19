"""Independent technical original-game ScummVM capture audit on pinned saved state.
Compares new original-game frame from pinned evidence save to previous original frame.
Not a native ZORKDOS or Godot gameplay-fidelity comparison.
"""
from pathlib import Path
import hashlib,json,stat,wave
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
from fidelity_runtime_worker_v1 import validate_capture
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-pinned-vb30-supervised-sequence-v7-r1"
old=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
master=run/"fidelity-isolated"/"capture"/"capture-attestation.json"
pinned=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
proof=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"pinned-save-manifest.json"
m=json.loads(master.read_text(encoding="utf-8"))
v=json.loads((run/"result.json").read_text(encoding="utf-8"))
ctrl=json.loads((run/"control-receipt.json").read_text(encoding="utf-8"))
val=json.loads((run/"validation-result.json").read_text(encoding="utf-8"))
fidelity_acceptance=json.loads((run/"acceptance-result.json").read_text(encoding="utf-8"))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert len(m["frames"])==3
assert [r["requested_at_seconds"] for r in m["frames"]]==[3,8,14]
assert verify_bounded_wgc_sequence(master.parent,m)["verified_frames"]==3
assert ctrl["status"]=="BLOCKED" and v["status"]=="BLOCKED"
assert v["diagnostic_capture_status"]=="PASS" and v["exit_code"]==0
assert val["status"]=="FAIL" and fidelity_acceptance["status"]=="FAIL"
assert v["registered_target"]["project"]=="OpenZork"
assert v["registered_target"]["runtime_kind"]=="scummvm"
assert v["registered_target"]["classification"]=="SCUMMVM_CROSS_VALIDATION_NOT_NATIVE_DOS"
assert v["game_source_binding"]["status"]=="PASS_SOURCE_BOUND"
assert Path(v["game_source_binding"]["config_game_root"])==(R/"source"/"Zork Nemesis")
assert v["save_seed_materialization"]["entries"][0]["source_kind"]=="PINNED_EVIDENCE"
assert v["save_seed_materialization"]["entries"][0]["seed_scene"]=="vb30"
assert v["save_seed_materialization"]["entries"][0]["seed_view"]==1058
assert sha(pinned)==sha(Path(v["save_seed_materialization"]["entries"][0]["private_copy_path"]))
assert sha(pinned)==json.loads(proof.read_text(encoding="utf-8"))["pinned_sha256"]
assert not pinned.stat().st_mode & stat.S_IWRITE
hashes={r["sha256"] for r in m["frames"]}
assert len(hashes)==1
pics=[]
for frame in m["frames"]:
 with Image.open(master.parent/frame["path"]) as i:
  im=i.convert("RGB")
  assert im.size==(962,768)
  pics.append(np.asarray(im,dtype=np.uint8))
assert all(np.array_equal(pics[0],x) for x in pics[1:])
roi=(96,167,864,647)
with Image.open(master.parent/m["frames"][0]["path"]) as im:
 latest=im.convert("RGB").crop(roi)
 latest_file=run/"pinned-vb30-viewport-768x480.png"
 latest.save(latest_file)
latest_np=np.asarray(latest,dtype=np.int16)
old_file=old/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"
with Image.open(old_file) as im:
 prior=im.convert("RGB")
prior_np=np.asarray(prior,dtype=np.int16)
assert latest_np.shape==prior_np.shape==(480,768,3)
delta=np.abs(latest_np-prior_np)
full_mae=float(delta.mean())
changed=float(np.any(delta>8,axis=2).mean())
new_hash=sha(latest_file);old_hash=sha(old_file)
if np.array_equal(latest_np,prior_np):comparison="PIXEL_EXACT"
else:comparison="FRAME_DIFFERENCE_OBSERVED_CANNOT_ASSUME_IDENTICAL_STATE"
difference=Image.fromarray(delta.clip(0,255).astype(np.uint8),"RGB")
diffpath=run/"pinned-vb30-vs-prev-golden-diff.png"
difference.save(diffpath)
with wave.open(str(master.parent/"process-0001.wav"),"rb") as w:
 pcm=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float64)
 rms=round(float(np.sqrt((pcm*pcm).mean())),3) if pcm.size else 0.
record={
 "schema":"OpenZork.PinnedSupervisedOriginalSceneCapture.v1",
 "status":"LOCAL_PINNED_SOURCE_VIDEO_AUDIO_TECHNICAL_PASS_FIDELITY_HOLD",
 "run_id":run.name,
 "scene":"VB30","saved_view":1058,
 "runtime":"SCUMMVM_2.0_ZVISION_NOT_NATIVE_ZORKDOS",
 "registered_executable_sha256":v["registered_target"]["executable_sha256"],
 "registered_game_root":v["game_source_binding"]["config_game_root"],
 "pinned_save_sha256":sha(pinned),
 "same_process_PID":m["pid"],"same_process_HWND":m["hwnd"],
 "frames":[{"at":frame["requested_at_seconds"],"sha256":frame["sha256"]} for frame in m["frames"]],
 "three_frame_pixel_identical":True,
 "viewport_new_sha256":new_hash,
 "viewport_prior_sha256":old_hash,
 "comparison_to_prior_saved_capture":comparison,
 "viewport_MAE_vs_prior":round(full_mae,5),
 "viewport_changed_fraction_gt8":round(changed,7),
 "delta_image":str(diffpath),
 "audio_wav_sha256":sha(master.parent/"process-0001.wav"),
 "audio_rms":rms,
 "clean_runtime_exit":True,
 "fidelity_gate_status":"BLOCKED_EXPECTED",
 "source_files_modified":False,
 "reconstruction_fidelity_verification":"NOT_TESTED"}
dest=run/"pinned-capture-evidence-v7.json"
if dest.exists():raise RuntimeError("PINNED_CAPTURE_AUDIT_ALREADY_EXISTS")
dest.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"frames_identical":True,
 "across_original_runs":comparison,"cross_run_MAE":record["viewport_MAE_vs_prior"],
 "fraction_changed":record["viewport_changed_fraction_gt8"],
 "new_viewport_sha256":new_hash,
 "original_audio_rms":rms,"fidelity":"HOLD",
 "report":str(dest)},ensure_ascii=False))
