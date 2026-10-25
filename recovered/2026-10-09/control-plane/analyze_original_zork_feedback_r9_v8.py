"""Independent native ZORKDOS original runtime feedback replay analysis.
All WGC samples and pre-click observations are local, owned and SHA-pinned.
Visual gameplay state classification requires inspecting the contact sheet.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
from fidelity_local_capture_wgc_v1 import _read_bmp_dimensions
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-cursor-feedback-newgame-20261009-r9"
out=R/"runtime-test"/"results"/rid
folder=out/"fidelity-isolated"/"capture"
master=folder/"capture-attestation.json"
trace=out/"feedback-guest-mouse-trace.json"
run=out/"result.json"
manifest=json.loads(master.read_text(encoding="utf-8-sig"))
t=json.loads(trace.read_text(encoding="utf-8-sig"))
worker=json.loads(run.read_text(encoding="utf-8-sig"))
assert verify_bounded_wgc_sequence_v2(folder,manifest)["verified_frames"]==5
assert manifest["pid"]==worker["runtime_identity"]["pid"] and worker["exit_code"]==0
assert all(x["result"]["runtime_pid"]==manifest["pid"] and
 x["result"]["lease_epoch"]==manifest["run_token"] for x in t["supervised_peer_binding"])
assert all(x["native_WGC_attestation_sha256"] for x in t["cursor_feedback_observations"])
frames=[];images=[]
for entry in manifest["frames"]:
 path=folder/entry["path"]
 with Image.open(path) as im:
  rgb=im.convert("RGB")
  png=path.with_suffix(".png")
  rgb.save(png)
  arr=np.asarray(rgb,dtype=np.uint8)
 frames.append({"t":entry["requested_at_seconds"],
 "sha256":entry["sha256"],"png":str(png),
 "mean_rgb":arr.astype(np.float64).mean((0,1)).round(2).tolist()})
 images.append(arr)
h,w=images[0].shape[:2]
assert all(x.shape==images[0].shape for x in images)
canvas=Image.new("RGB",(w*3+26,2*(h+43)+5),(13,13,13))
draw=ImageDraw.Draw(canvas)
for i,arr in enumerate(images):
  x=(i%3)*(w+8)+6;y=(i//3)*(h+43)+31
  canvas.paste(Image.fromarray(arr,"RGB"),(x,y))
  draw.text((x,y-20),f"Native ZORKDOS t={frames[i]['t']}s",fill=(245,245,245))
sheet=out/"native-zork-feedback-fivepoint-contact.png"
canvas.save(sheet)
metrics=[]
for a,b in zip(images,images[1:]):
 d=np.abs(a.astype(np.int16)-b.astype(np.int16))
 metrics.append({"MAE":round(float(d.mean()),5),
 "fraction_changed_gt20":round(float(np.any(d>20,axis=2).mean()),6)})
evidence={
 "schema":"OpenZork.OriginalNativeGameMouseCalibrationReplayEvidence.v1",
 "status":"ACTUAL_NATIVE_GAME_FRAME_SEQUENCE_CAPTURED_REPLAY_CLASSIFICATION_PENDING",
 "run":rid,"original_ZORKDOS_corpus_read_only":True,
 "runtime_exe_sha256":manifest["executable_sha256"],
 "owner_pid":manifest["pid"],"owner_hwnd":manifest["hwnd"],
 "owner_creation_time":manifest["creation_ticks_100ns"],
 "mcp_PIDs_lease_attested":True,
 "preclick_frame_authorized":t["button_press_released"],
 "movie_skip_space_sent":t["movie_skip_space_sent"],
 "feedback_observations":[{"status":r["cursor"]["status"],
 "xy":[r["cursor"]["x"],r["cursor"]["y"]],"native_frame_sha256":r["frame_sha256"],
 "move":r.get("bounded_positive_guest_motion")} for r in t["cursor_feedback_observations"]],
 "original_frames":frames,"adjacent_visual_delta":metrics,
 "original_source_playable_scene":"NOT_YET_VERIFIED_BY_VISUAL_REVIEW",
 "original_vs_Godot_fidelity":"HOLD",
 "global_host_cursor_focus_events":0,
 "contact_sheet":str(sheet),"contact_sheet_sha256":hashlib.sha256(sheet.read_bytes()).hexdigest()}
dest=out/"feedback-gameplay-original-observation-v8.json"
if dest.exists():raise RuntimeError("R9_VERIFICATION_RESULT_ALREADY_EXISTS")
dest.write_text(json.dumps(evidence,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":evidence["status"],
 "mouse_click":evidence["preclick_frame_authorized"],"movie_skip":evidence["movie_skip_space_sent"],
 "steps":evidence["feedback_observations"],
 "frames":[{"t":f["t"],"sha":f["sha256"]} for f in frames],
 "diff":metrics,"contact_sheet":str(sheet),"evidence":str(dest)},ensure_ascii=False))
