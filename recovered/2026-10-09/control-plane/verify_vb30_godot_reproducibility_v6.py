"""Two independent Godot-headless outputs, byte-for-byte deterministic,
with a separate local ScummVM original captured at same saved scene and view.
No gameplay/interaction/full fidelity claim.
"""
import hashlib,json
from pathlib import Path
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parents[2]
prefix="openzork-vb30-1058-godot-headless-20261009-"
runs=[R/"runtime-test"/"results"/(prefix+ver) for ver in ("r2","r3")]
imgs=[r/"engine-vb30-1058.png" for r in runs]
orig=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
source_capture=orig/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"
pose=orig/"vb30-save-scene-pose-and-decoder-v6.json"
assert all(p.is_file() for p in (imgs[0],imgs[1],source_capture,pose))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
worker=[]
pictures=[]
for i,r in enumerate(runs):
 rec=json.loads((r/"control-receipt.json").read_text(encoding="utf-8"))
 result=json.loads((r/"result.json").read_text(encoding="utf-8"))
 assert rec["status"]=="PASS" and rec["validation_status"]=="PASS" and rec["acceptance_status"]=="PASS"
 assert result["status"]=="PASS" and result["exit_code"]==0
 log=(r/"stdout.log").read_text(encoding="utf-8")
 assert "OPENZORK_FIDELITY_CANDIDATE_READY VB30@1058" in log
 assert "OPENREMASTER_VB30_1058_GODOT_RUNTIME_CAPTURE_PASS" in log
 worker.append({"run_id":r.name,"receipt_sha256":sha(r/"control-receipt.json"),
                "exe_sha256":result["fingerprint"]["godot_sha256"],
                "project_godot_sha256":result["fingerprint"]["project_godot_sha256"],
                "file_sha256":sha(imgs[i]),"runtime_exit":0})
 with Image.open(imgs[i]) as im:
  pictures.append(np.asarray(im.convert("RGB"),dtype=np.uint8))
assert pictures[0].shape==pictures[1].shape==(320,512,3)
pixel_identity=bool(np.array_equal(pictures[0],pictures[1]))
same_png=imgs[0].read_bytes()==imgs[1].read_bytes()
assert pixel_identity and same_png,(pixel_identity,same_png)
assert worker[0]["exe_sha256"]==worker[1]["exe_sha256"]
assert worker[0]["project_godot_sha256"]==worker[1]["project_godot_sha256"]
pose_e=json.loads(pose.read_text(encoding="utf-8"))
assert pose_e["status"]=="SAVE_LOCATION_AND_TGZ_DECODER_BYTE_MATCH_PASS"
assert pose_e["location_key"]=="VB30" and pose_e["view_coordinate"]==1058
visual=json.loads((runs[0]/"vb30-matched-original-vs-godot-technical-comparison.json").read_text())
assert visual["status"]=="MATCHED_SCENE_AND_POSE_PIXEL_COMPARISON_COMPLETE_FIDELITY_HOLD"
assert visual["cpu_projection_exact_match"] is True

contract={
 "schema":"OpenZork.VB30ReconstructedFrameRepeatability.v1",
 "status":"REAL_GODOT_REPEATABLE_PIXEL_IDENTICAL_MATCHED_SCENE_TECHNICAL_PASS_FIDELITY_HOLD",
 "project":"OpenZork",
 "scene":"VB30","original_view":1058,
 "save_sha256":pose_e["save_sha256"],
 "source_tgz_sha256":pose_e["location_source_sha256"],
 "source_tgz_decoding_hash_match":pose_e["decoded_ppm_matches_preexisting"],
 "original_scummvm_768x480_sha256":sha(source_capture),
 "godot_runtime_version":"4.7.2.stable",
 "two_orch_k003_runs":worker,
 "exact_engine_png_identical":same_png,
 "exact_engine_pixels_identical":pixel_identity,
 "original_vs_godot_visual_metrics":visual["pixel_metrics"],
 "original_runtime_image_aligned_at_same_save_scene_view":True,
 "cpu_projected_pixels_identical_to_godot":True,
 "sound_audio_reconstruction":"NOT_VERIFIED",
 "gameplay_saved_state_loaded_in_godot":"NOT_VERIFIED",
 "gameplay_input":"NOT_VERIFIED",
 "retail_or_native_DOS_original_runtime_comparison":"NOT_VERIFIED",
 "original_visual_reconstruction_full_fidelity":"HOLD",
 "conclusion":"TECHNICAL_STATIC_VIEW_ACCEPTED_FOR_CROSSVALIDATION_ONLY",
 "original_engine":"SCUMMVM_ZVISION",
 "candidate_engine":"GODOT_HEADLESS_RUNTIME",
 "source_corpus_mutated":False
}
dest=runs[1]/"vb30-repeatable-static-view-checkpoint.json"
dest.write_text(json.dumps(contract,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":contract["status"],"pixel_identity":pixel_identity,
 "png_file_sha256":worker[0]["file_sha256"],
 "original_save":contract["scene"]+"@"+str(contract["original_view"]),
 "original_v_godot_mae":visual["pixel_metrics"]["godot_vs_scummvm_original_bilinear"],
 "both_runtime_runs_EXIT0":True,"evidence":str(dest)}))
