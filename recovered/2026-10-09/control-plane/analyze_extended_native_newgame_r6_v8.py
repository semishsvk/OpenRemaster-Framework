"""Independent r6 original ZORKDOS late gameplay frame analysis.
Read-only v2 WGC master + nested samples, exact MCP TCP peer identity and lease.
One 4-frame contact sheet from real original-game WGC, no AI imagery and no fidelity promotion.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-native-dosboxx-extended-newgame-20261009-r6"
base=run/"fidelity-isolated"/"capture"
master=base/"capture-attestation.json"
tracepath=run/"authenticated-MCP-original-native-input-trace.json"
src=run/"result.json"
out=run/"late-original-game-scene-v8-evidence.json"
assert not out.exists()
m=json.loads(master.read_text(encoding="utf-8-sig"))
t=json.loads(tracepath.read_text(encoding="utf-8-sig"))
r=json.loads(src.read_text(encoding="utf-8-sig"))
proof=verify_bounded_wgc_sequence_v2(base,m)
assert proof["verified_frames"]==4
assert m["run_token"]==t["first_peer_attestation"]["lease_epoch"]==t["pre_input_peer_attestation"]["lease_epoch"]
assert m["pid"]==t["first_peer_attestation"]["runtime_pid"]==r["runtime_identity"]["pid"]
assert m["creation_ticks_100ns"]==t["pre_input_peer_attestation"]["runtime_creation_ticks"]
assert m["executable_sha256"]==t["original_emulator_executable_sha256"]==r["runtime_identity"]["executable_sha256"]
assert t["status"]=="EXACT_SUPERVISED_PID_LEASE_BOUND_INPUT_COMMANDS_ISSUED"
assert r["diagnostic_capture_status"]=="PASS" and r["exit_code"]==0
assert [x["requested_at_seconds"] for x in m["frames"]]==[35,42,55,70]
rows=[];images=[]
for row in m["frames"]:
 p=base/row["path"]
 with Image.open(p) as im:
  rgb=im.convert("RGB")
  png=p.with_suffix(".png")
  rgb.save(png)
  image=np.asarray(rgb,dtype=np.uint8)
 rows.append({"time_seconds":row["requested_at_seconds"],
  "actual_capture_start_seconds":row["started_at_seconds"],
  "frame_file":str(p),"preview_png":str(png),
  "sha256":row["sha256"],"dimension":[rgb.width,rgb.height],
  "mean_rgb":np.asarray(image,dtype=np.float64).mean((0,1)).round(2).tolist()})
 images.append(image)
h,w=images[0].shape[:2]
assert all(a.shape==(h,w,3) for a in images)
sheet=Image.new("RGB",(w*2+24,(h+45)*2+8),(13,13,13))
draw=ImageDraw.Draw(sheet)
for i,im in enumerate(images):
 x=(i%2)*(w+12)+4
 y=(i//2)*(h+45)+34
 sheet.paste(Image.fromarray(im,"RGB"),(x,y))
 draw.text((x,y-23),f"Real native ZORKDOS  t={rows[i]['time_seconds']}s",fill=(240,240,240))
contact=run/"native-original-newgame-extended-4frame-contact.png"
sheet.save(contact)
stats=[]
for a,b in zip(images,images[1:]):
 delta=np.abs(a.astype(np.int16)-b.astype(np.int16))
 stats.append({"mean_absolute_rgb":round(float(delta.mean()),5),
  "changed_pixel_fraction_gt20":round(float(np.any(delta>20,axis=2).mean()),7)})
record={
 "schema":"OpenZork.NativeZorkDOSAuthenticatedNewGameLateCapture.v1",
 "status":"BOUND_ORIGINAL_GAME_LATE_CAPTURE_TECHNICAL_PASS_GAMEPLAY_STATE_REVIEW_REQUIRED",
 "frame_samples":rows,"adjacent_frame_metrics":stats,
 "contact_sheet":str(contact),
 "contact_sheet_sha256":hashlib.sha256(contact.read_bytes()).hexdigest(),
 "verified_schedule":"OpenRemaster.BoundedFrameSchedule.v2",
 "pid":m["pid"],"hwnd":m["hwnd"],
 "creation_ticks_100ns":m["creation_ticks_100ns"],
 "exe_sha256":m["executable_sha256"],
 "identity_binding":"EXACT_SOCKET_PID_CREATION_TIME_EXECUTABLE_SHA256_AND_GUI_LEASE",
 "game_source_provenance":r.get("game_source_binding"),
 "input_events":["guest_relative_Y_110","left_press","left_release"],
 "host_global_mouse_events":0,
 "technical_status":"PASS","original_reconstruction_fidelity":"NOT_VERIFIED",
 "native_gameplay_scene_verified":False
}
out.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"run_id":run.name,
"frames":[{"t":e["time_seconds"],"sha256":e["sha256"],"mean":e["mean_rgb"]} for e in rows],
"changes":stats,"contact_sheet":str(contact),"evidence":str(out)}))
