"""Independent diagnostic analysis: actual ZORKDOS original title click, film skip and
late same-PID WGC frames. Compare to no-Space control r6; no fabricated game state.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"
ctrl=R/"runtime-test"/"results"/"openzork-native-dosboxx-extended-newgame-20261009-r6"
folder=run/"fidelity-isolated"/"capture"
master=folder/"capture-attestation.json"
trace=run/"authenticated-guest-newgame-spacebar-trace.json"
result=run/"result.json"
out=run/"newgame-spacebar-fivepoint-observation.json"
assert not out.exists(),"SKIP_ANALYSIS_EXISTS"
m=json.loads(master.read_text(encoding="utf-8-sig"))
t=json.loads(trace.read_text(encoding="utf-8-sig"))
r=json.loads(result.read_text(encoding="utf-8-sig"))
v=verify_bounded_wgc_sequence_v2(folder,m)
assert v["status"]=="PASS_TECHNICAL_CAPTURE_ONLY" and v["verified_frames"]==5
assert [row["requested_at_seconds"] for row in m["frames"]]==[35,43,54,66,73]
assert m["pid"]==r["runtime_identity"]["pid"] and m["hwnd"]==r["runtime_window"]["hwnd"]
assert m["creation_ticks_100ns"]==t["supervised_peer_attestations"][0]["binding"]["runtime_creation_ticks"]
assert m["executable_sha256"]==r["registered_target"]["executable_sha256"]
assert all(x["binding"]["runtime_pid"]==m["pid"] and x["binding"]["lease_epoch"]==m["run_token"]
           for x in t["supervised_peer_attestations"])
assert t["status"]=="EXACT_PROCESS_BOUND_MENU_CLICK_AND_GUEST_SPACE_DELIVERED_GAME_STATE_PENDING"
assert r["diagnostic_capture_status"]=="PASS" and r["exit_code"]==0
imgs=[];rows=[]
for row in m["frames"]:
 f=folder/row["path"]
 with Image.open(f) as im:
  im=im.convert("RGB")
  png=f.with_suffix(".png")
  im.save(png)
  raw=np.asarray(im,dtype=np.uint8)
 imgs.append(raw)
 rows.append({"t":row["requested_at_seconds"],
    "real_t":row["started_at_seconds"],
    "sha256":row["sha256"],
    "png":str(png),"height":raw.shape[0],"width":raw.shape[1],
    "rgb_mean":np.asarray(raw,dtype=np.float64).mean((0,1)).round(2).tolist()})
w,h=imgs[0].shape[1],imgs[0].shape[0]
assert all(x.shape==imgs[0].shape for x in imgs)
sheet=Image.new("RGB",(w*3+36,(h+42)*2+10),(9,9,9))
pen=ImageDraw.Draw(sheet)
for i,img in enumerate(imgs):
 col=i%3;row=i//3
 x=col*(w+12)+6;y=row*(h+42)+35
 sheet.paste(Image.fromarray(img,"RGB"),(x,y))
 pen.text((x,y-22),f"Original DOS ZORKDOS t={rows[i]['t']}s",fill="white")
sheetpath=run/"original-native-space-skip-fivepoint-contact.png"
sheet.save(sheetpath)
ctrl_dir=ctrl/"fidelity-isolated"/"capture"/"samples"
compare=[]
# Control r6 movie frames around same stage: 55s and 70s.
for r7_i,r6_i in ((2,3),(3,4),(4,4)):
 cf=ctrl_dir/("point-%02d"%r6_i)/"frame-0001.bmp"
 with Image.open(cf) as p:
  B=np.asarray(p.convert("RGB"),dtype=np.int16)
 A=imgs[r7_i].astype(np.int16)
 if A.shape==B.shape:
  delta=np.abs(A-B)
  compare.append({"r7_t":rows[r7_i]["t"],
     "r6_nomovieskip_sample":(55 if r6_i==3 else 70),
     "MAE":round(float(delta.mean()),3),
     "fraction_changed_gt20":round(float(np.any(delta>20,axis=2).mean()),6)})
changes=[]
for a,b in zip(imgs,imgs[1:]):
 delta=np.abs(a.astype(np.int16)-b.astype(np.int16))
 changes.append({"MAE":round(float(delta.mean()),4),
  "changed_fraction_gt20":round(float(np.any(delta>20,axis=2).mean()),6)})
record={
 "schema":"OpenZork.OriginalNativeDOSNewGameSpacebarSkipObservation.v1",
 "status":"ORIGINAL_SAME_OWNER_5_FRAME_CAPTURE_INPUT_AUTHENTICATED_GAME_STATE_VISUAL_REVIEW",
 "time_utc":datetime.now(timezone.utc).isoformat(),
 "run_id":run.name,"registered_runtime":"DOSBOX_X_2026_10_01_SOURCE_ZORKDOS_READ_ONLY",
 "original_executable_sha256":m["executable_sha256"],
 "owner_pid":m["pid"],"owner_creation":m["creation_ticks_100ns"],
 "owner_hwnd":m["hwnd"],"owner_epoch":m["run_token"],
 "three_authenticated_peer_checks":len(t["supervised_peer_attestations"])==3,
 "guest_events":"NEWGAME_MOVE_AND_CLICK_THEN_SPACE_MOVIE_SKIP",
 "frames":rows,"adjacent_difference":changes,"control_no_movie_skip":compare,
 "original_capture_proof":v,"contact_sheet":str(sheetpath),
 "contact_sheet_sha256":hashlib.sha256(sheetpath.read_bytes()).hexdigest(),
 "producer_original_WGC":True,"remote_desktop_stream_fidelity_authority":False,
 "global_mouse_keyboard_actions":0,
 "first_playable_original_scene_verified":False,
 "original_vs_reconstruction_fidelity":"NOT_PERFORMED",
 "gameplay_input_adapter":"EXPERIMENTAL_LOOPBACK_DIAGNOSTIC_ONLY"
}
out.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"frames":[{"t":e["t"],"sha256":e["sha256"],"means":e["rgb_mean"]} for e in rows],
"change":changes,"comparison_no_skip":compare,"contact_sheet":str(sheetpath),"evidence":str(out)}))
