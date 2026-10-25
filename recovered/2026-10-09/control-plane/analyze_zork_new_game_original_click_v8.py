"""Evidence-based native DOS Zork New Game emulated-click test:
verify same registered original runtime, exact guest OUTD input trace, capture 3 frames,
and compare final after-click to prior MOVE-ONLY title. Actual gameplay state via visual review.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-mcp-new-game-click-20261009-r5"
run=R/"runtime-test"/"results"/rid
mfile=run/"fidelity-isolated"/"capture"/"capture-attestation.json"
trace=run/"MCP-newgame-original-native-input-trace.json"
result=run/"result.json"
control=R/"runtime-test"/"results"/"openzork-native-dosboxx-live-mousemove-20261009-r4"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp"
output=run/"native-newgame-click-analysis.json"
if output.exists():raise RuntimeError("CLICK_ANALYSIS_ALREADY_EXISTS_NO_OVERWRITE")
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
m=load(mfile) if mfile.is_file() else {}
t=load(trace) if trace.is_file() else {}
r=load(result) if result.is_file() else {}
v=None;rows=[];pixels=[]
if m:
 try:v=verify_bounded_wgc_sequence(mfile.parent,m)
 except Exception as e:v={"status":"FAIL","error":str(e)}
 for entry in m.get("frames") or []:
  p=mfile.parent/entry["path"]
  with Image.open(p) as source:
   im=source.convert("RGB")
   im.save(p.with_suffix(".png"))
   rows.append({"at":entry["requested_at_seconds"],"path":str(p.with_suffix(".png")),
     "frame_sha256":entry["sha256"],"dimensions":[im.width,im.height]})
   pixels.append(np.asarray(im,dtype=np.uint8))
comparison={}
if len(pixels)==3:
 with Image.open(control) as source:
  baseline=np.asarray(source.convert("RGB"),dtype=np.uint8)
 for index,A in enumerate(pixels):
  label=f"frame_{index+1}_compared_to_prior_move_only_title"
  if A.shape!=baseline.shape:
   comparison[label]={"different_window_dimensions":[list(A.shape),list(baseline.shape)]}
  else:
   diff=np.abs(A.astype(np.int16)-baseline.astype(np.int16))
   changed=np.any(diff>20,axis=2)
   comparison[label]={"MAE_0_255":round(float(diff.mean()),4),
    "fraction_pixels_gt20":round(float(changed.mean()),6)}
 width=max(x.shape[1] for x in pixels)
 height=max(x.shape[0] for x in pixels)
 sheet=Image.new("RGB",(width*3+20,height+60),(13,13,13))
 pen=ImageDraw.Draw(sheet)
 for i,image in enumerate(pixels):
  sheet.paste(Image.fromarray(image,"RGB"),(i*width+4,35))
  pen.text((i*width+8,10),f"Native Zork original t={rows[i]['at']}s",fill="white")
 contact=run/"newgame-native-click-threepoint-timeline.png"
 sheet.save(contact)
 comparison["contact_sheet"]=str(contact)
canary=(r.get("diagnostic_capture_status")=="PASS"
 and r.get("exit_code")==0
 and t.get("status")=="NATIVE_DOS_MOUSE_MOVE_CLICK_INJECTED_GAME_STATE_UNVERIFIED"
 and m.get("pid")==r.get("runtime_identity",{}).get("pid")
 and m.get("hwnd")==r.get("runtime_window",{}).get("hwnd")
 and v and v.get("status")=="PASS_TECHNICAL_CAPTURE_ONLY"
 and len(pixels)==3)
rec={
 "schema":"OpenZork.NativeDOSBoxXNewGameGuestMouseClickObservation.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":"ORIGINAL_GUEST_CLICK_AND_THREE_LOCAL_CAPTURE_FRAMES_PASS_GAME_STATE_PENDING" if canary else "ORIGINAL_GUEST_CLICK_EVIDENCE_HOLD",
 "run_id":rid,
 "original_runtime":"REGISTERED_DOSBOX_X_ZORKDOS.EXE_READ_ONLY_SOURCE",
 "emulator_mouse_input":"INTEGRATION_DEVICE_MOUSE_MOVE_PRESS_RELEASE",
 "guest_input_trace_sha256":hashlib.sha256(trace.read_bytes()).hexdigest() if trace.is_file() else None,
 "frames":rows,
 "control_original_run":"openzork-native-dosboxx-live-mousemove-20261009-r4",
 "control_original_title_frame_sha256":hashlib.sha256(control.read_bytes()).hexdigest(),
 "compare_to_control":comparison,
 "raw_ORCH_exit":r.get("exit_code"),
 "local_wgc_PID":m.get("pid"),"local_wgc_HWND":m.get("hwnd"),
 "native_new_game_selected":"NOT_ATTESTED_FROM_NUMERIC_DIFFERENCE",
 "fidelity_gate":"HOLD","full_original_vs_Godot_replay":"NOT_PERFORMED",
 "global_host_input_events":0,"canonical_original_game_files_modified":False}
output.write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":rec["status"],"frames":rows,
"control_metrics":comparison,"trace":t.get("status"),
"evidence":str(output)},ensure_ascii=False))
raise SystemExit(0 if canary else 1)
