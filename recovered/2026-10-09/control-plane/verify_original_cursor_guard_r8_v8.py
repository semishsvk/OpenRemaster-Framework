"""Review exact owned-WGC pre-click guard and bounded original ZORKDOS timeline.
Classification: click authorized vs safely blocked; film/gameplay never assumed.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
from fidelity_original_cursor_gate_v1 import evaluate_original_newgame_cursor
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"
capture=run/"fidelity-isolated"/"capture"
mfile=capture/"capture-attestation.json"
trace=run/"cursor-guarded-original-newgame-input-trace.json"
worker=run/"result.json"
report=run/"cursor-guarded-original-gameplay-observation-v8.json"
assert not report.exists(),"R8_OBSERVATION_ALREADY_EXISTS"
m=json.loads(mfile.read_text(encoding="utf-8-sig"))
t=json.loads(trace.read_text(encoding="utf-8-sig"))
w=json.loads(worker.read_text(encoding="utf-8-sig"))
assert verify_bounded_wgc_sequence_v2(capture,m)["verified_frames"]==5
assert w.get("exit_code")==0 and w.get("diagnostic_capture_status")=="PASS"
assert m["pid"]==w["runtime_identity"]["pid"]
gate=t.get("source_cursor_gate")
assert gate is not None
input_img=Path(t["WGC_pre_click_capture"]["frame_path"])
again=evaluate_original_newgame_cursor(input_img)
assert again["status"]==gate["status"] and again["original_frame_sha256"]==gate["original_frame_sha256"]
assert t["click_sent"]==gate["authorized_single_mouse_click"],(t["click_sent"],gate)
assert t["space_sent"]<=t["click_sent"]
frames=[];arrays=[]
for row in m["frames"]:
 path=capture/row["path"]
 with Image.open(path) as im:
  rgb=im.convert("RGB");png=path.with_suffix(".png")
  rgb.save(png)
  arr=np.asarray(rgb,dtype=np.uint8)
 frames.append({"offset_s":row["requested_at_seconds"],
   "frame_sha256":row["sha256"],"png":str(png)})
 arrays.append(arr)
assert all(a.shape==arrays[0].shape for a in arrays)
height,width=arrays[0].shape[:2]
sheet=Image.new("RGB",(width*3+28,(height+40)*2),(12,12,12))
draw=ImageDraw.Draw(sheet)
for i,arr in enumerate(arrays):
 x=(i%3)*(width+8)+4;y=(i//3)*(height+40)+30
 sheet.paste(Image.fromarray(arr,"RGB"),(x,y))
 draw.text((x,y-21),f"Native ZORKDOS t={frames[i]['offset_s']}s",fill="white")
contact=run/"cursor-guarded-native-original-fivepoint-timeline.png"
sheet.save(contact)
late_same=all(np.array_equal(arrays[2],a) for a in arrays[3:])
metrics=[]
for a,b in zip(arrays,arrays[1:]):
 d=np.abs(a.astype(np.int16)-b.astype(np.int16))
 metrics.append({"MAE":round(float(d.mean()),5),
   "fraction_changed_gt20":round(float(np.any(d>20,axis=2).mean()),6)})
r={
 "schema":"OpenZork.NativeOriginalGuardedMouseReplayVerification.v1",
 "status":"INPUT_GUARD_POSITIVE_CLICK_AND_SPACE_DIAGNOSTIC_CAPTURE" if t["click_sent"] and t["space_sent"]
        else "INPUT_GUARD_NEGATIVE_SAFE_NO_CLICK_DIAGNOSTIC_CAPTURE",
 "run_id":run.name,"source_cursor_original_sha256":gate["source_sprite_sha256"],
 "pre_click_bound_frame_sha256":gate["original_frame_sha256"],
 "position":gate["best_cursor_top_left"],
 "template_RMSE":gate["best_template_RGB_RMSE"],
 "click_authorized":t["click_sent"],"space_sent":t["space_sent"],
 "all_in_run_frame_SHA_and_owner_verified":True,
 "frame_sequence":frames,"adjacent_metrics":metrics,
 "late_frames_54_66_73_equal":late_same,
 "contact_sheet":str(contact),
 "guest_gameplay_state_verified":False,
 "original_vs_Godot_replay_verified":False,
 "fidelity_verified":False,"no_global_windows_input":True
}
report.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":r["status"],"gate":gate["status"],
 "best_cursor":gate["best_cursor_top_left"],"rmse":gate["best_template_RGB_RMSE"],
 "clicked":r["click_authorized"],"space_sent":r["space_sent"],
 "metrics":metrics,"late_frames_same":late_same,
 "contact_sheet":str(contact),"evidence":str(report)},ensure_ascii=False))
