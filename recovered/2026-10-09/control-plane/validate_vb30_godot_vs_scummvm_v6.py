"""Independent read-only original-versus-actual-Godot-VB30 technical comparison.
Never award gameplay/interaction/audio fidelity from single static frame.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[2]
src_dir=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
run=R/"runtime-test"/"results"/"openzork-vb30-1058-godot-headless-20261009-r2"
godot=run/"engine-vb30-1058.png"
cpu=src_dir/"vb30-savepose-source-CPU-projection-512x320.png"
original=src_dir/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"
pose=src_dir/"vb30-save-scene-pose-and-decoder-v6.json"
manifest=src_dir/"fidelity-isolated"/"capture"/"capture-attestation.json"
receipt=run/"control-receipt.json"
worker=run/"result.json"
stdout=run/"stdout.log"
for p in (godot,cpu,original,pose,manifest,receipt,worker,stdout):
 assert p.is_file(),str(p)
save_pose=json.loads(pose.read_text())
assert save_pose["status"]=="SAVE_LOCATION_AND_TGZ_DECODER_BYTE_MATCH_PASS"
assert (save_pose["location_key"],save_pose["view_coordinate"])==("VB30",1058)
r=json.loads(receipt.read_text())
j=json.loads(worker.read_text())
assert r["status"]=="PASS" and r["validation_status"]=="PASS" and r["acceptance_status"]=="PASS"
assert j["status"]=="PASS" and j["mode"]=="headless" and j["exit_code"]==0
assert j["fingerprint"]["remote_desktop_capture_authority"] is False
logs=stdout.read_text(encoding="utf-8")
assert "OPENZORK_FIDELITY_CANDIDATE_READY VB30@1058" in logs
assert "OPENREMASTER_VB30_1058_GODOT_RUNTIME_CAPTURE_PASS" in logs
with Image.open(godot) as im:g=np.array(im.convert("RGB"),dtype=np.uint8)
with Image.open(cpu) as im:c=np.array(im.convert("RGB"),dtype=np.uint8)
with Image.open(original) as im:
 orig=im.convert("RGB")
 refn=np.array(orig.resize((512,320),Image.Resampling.NEAREST),dtype=np.uint8)
 refb=np.array(orig.resize((512,320),Image.Resampling.BILINEAR),dtype=np.uint8)
assert g.shape==c.shape==refn.shape==(320,512,3)

def metric(a,b,mask=False):
 a=a.astype(np.float32);b=b.astype(np.float32)
 if mask:
  # Exploratory exclusion of visible ScummVM cursor and nearby pixels.
  a=a[55:,80:,:];b=b[55:,80:,:]
 d=np.abs(a-b)
 xa=a.mean(axis=2).ravel();xb=b.mean(axis=2).ravel()
 corr=float(np.corrcoef(xa,xb)[0,1]) if xa.std()>0 and xb.std()>0 else 0.0
 return {"mae":round(float(d.mean()),5),"corr":round(corr,7),
         "pixel_fraction_gt_10":round(float(np.any(d>10,axis=2).mean()),6),
         "max_channel_delta":int(d.max())}
cpu_godot=metric(g,c)
analysis={
 "godot_vs_cpu_prior_projection":cpu_godot,
 "godot_vs_scummvm_original_nearest":metric(g,refn),
 "godot_vs_scummvm_original_bilinear":metric(g,refb),
 "godot_vs_scummvm_original_bilinear_cursor_excluded":metric(g,refb,True)
}
cpu_exact=bool(np.array_equal(g,c))
delta=np.abs(g.astype(np.int16)-refb.astype(np.int16)).clip(0,255).astype(np.uint8)
diff=run/"godot-vb30-vs-scummvm-golden-diff.png"
Image.fromarray(delta,"RGB").save(diff)
sheet=Image.new("RGB",(1040,684),(20,20,20))
pen=ImageDraw.Draw(sheet)
sheet.paste(Image.fromarray(refn,"RGB"),(5,28))
sheet.paste(Image.fromarray(g,"RGB"),(522,28))
sheet.paste(Image.fromarray(c,"RGB"),(5,373))
sheet.paste(Image.fromarray(delta,"RGB"),(522,373))
pen.text((5,7),"ScummVM original scene VB30@1058",fill="white")
pen.text((522,7),"Actual Godot runtime engine frame",fill="white")
pen.text((5,350),"Prior source CPU projection",fill="white")
pen.text((522,350),"Abs Godot-vs-ScummVM difference",fill="white")
contact=run/"vb30-godot-runtime-vs-original-contact-sheet.png"
sheet.save(contact)
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={
 "schema":"OpenZork.ActualGodotVB30MatchedSceneTechnicalComparison.v1",
 "status":"MATCHED_SCENE_AND_POSE_PIXEL_COMPARISON_COMPLETE_FIDELITY_HOLD",
 "scene":"VB30","view":1058,
 "original_scummvm_corpus":"READ_ONLY_ZORK_NEMESIS",
 "original_scene_capture_provenance":h(manifest),
 "original_game_save_pose_provenance":h(pose),
 "original_frame_sha256":h(original),
 "godot_runtime_frame_sha256":h(godot),
 "cpu_projection_sha256":h(cpu),
 "headless_run_receipt_sha256":h(receipt),
 "headless_run_fingerprint":j["fingerprint"],
 "engine_emitted_scene_pose":True,
 "engine_frame_size":[512,320],
 "cpu_projection_exact_match":cpu_exact,
 "pixel_metrics":analysis,
 "cursor_mask":"exclude rows <55 and columns <80 only for exploratory metrics",
 "view_camera_alignment":"VB30 and angle verified from save file",
 "independent_visual_alignment":"SAME_SAVED_SCENE_POSE_AND_RESAMPLED_VIEWPORT_NOT_FULL_REPLAY",
 "golden_capture_engine":"SCUMMVM_ZVISION_NOT_NATIVE_DOS",
 "runtime_source_engine":"GODOT_4_7_2_ACTUAL_RUNTIME",
 "original_vs_candidate_audio":"NOT_TESTED",
 "hotspots_and_input_replay":"NOT_TESTED",
 "playable_replay":"NOT_VERIFIED",
 "retail_fidelity":"HOLD",
 "contact_sheet":str(contact),"difference_image":str(diff),
 "reconstruction_writes_to_source":"NONE"
}
dest=run/"vb30-matched-original-vs-godot-technical-comparison.json"
dest.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":record["schema"],"status":record["status"],
 "godot_cpu_exact":cpu_exact,"metrics":analysis,
 "frame_sha256":record["godot_runtime_frame_sha256"],
 "original_scene":"VB30@1058",
 "contact_sheet":str(contact),"evidence":str(dest)}))
