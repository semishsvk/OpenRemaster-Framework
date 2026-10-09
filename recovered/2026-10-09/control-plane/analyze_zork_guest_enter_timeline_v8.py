"""Real source native DOSBox-X ZORKDOS before/after debugger guest ENTER WGC timeline.
Technical evidence only; no input/gameplay/fidelity PASS inferred from command receipt.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-dosboxx-mcp-native-enter-20261009-r2"
trace=run/"guest-enter-MCP-trace.json"
capture=run/"fidelity-isolated"/"capture"
manifest=capture/"capture-attestation.json"
result=run/"result.json"
def load(p):return json.loads(p.read_text(encoding="utf-8-sig"))
T=load(trace) if trace.is_file() else {}
M=load(manifest) if manifest.is_file() else {}
W=load(result) if result.is_file() else {}
proof=None;arr=[];dimensions=[];rows=[]
if M:
 try:proof=verify_bounded_wgc_sequence(capture,M)
 except Exception as e:proof={"status":"FAIL","error":str(e)}
 for row in M.get("frames",[]):
  p=capture/row["path"]
  with Image.open(p) as im:
   converted=im.convert("RGB")
   converted.save(p.with_suffix(".png"))
   a=np.asarray(converted,dtype=np.uint8)
  arr.append(a);dimensions.append(a.shape)
  rows.append({"at":row["requested_at_seconds"],"file":str(p.with_suffix(".png")),
   "sha256":row["sha256"],"shape":list(a.shape)})
diff={}
if len(arr)==2 and arr[0].shape==arr[1].shape:
 a=arr[0].astype(np.int16);b=arr[1].astype(np.int16)
 D=np.abs(a-b);mask=np.any(D>20,axis=2)
 diff={"MAE":round(float(D.mean()),3),"pixel_fraction_gt20":round(float(mask.mean()),6),
       "hash_equal":rows[0]["sha256"]==rows[1]["sha256"]}
 side=Image.new("RGB",(arr[0].shape[1]*2+20,arr[0].shape[0]+70),(10,10,10))
 pen=ImageDraw.Draw(side)
 for i,image in enumerate(arr):
  x=8+i*(arr[0].shape[1]+5)
  side.paste(Image.fromarray(image,"RGB"),(x,35))
  pen.text((x,7),f"Native ZORKDOS sample {i+1} offset {rows[i]['at']}s",fill="white")
 sheet=run/"original-native-enter-before-after.png"
 side.save(sheet)
 diff["contact_sheet"]=str(sheet)
good=bool(T.get("status")=="ENTER_SCAN_INJECTED_VIA_GUEST_EMULATOR_NOT_GAMEPLAY_PROOF"
         and W.get("diagnostic_capture_status")=="PASS" and W.get("exit_code")==0
         and M.get("pid")==W.get("runtime_identity",{}).get("pid")
         and proof and proof.get("status")=="PASS_TECHNICAL_CAPTURE_ONLY")
r={
 "schema":"OpenZork.GuestKeyboardOriginalZorkFrames.v1",
 "status":"GUEST_INPUT_AND_ORIGINAL_CAPTURE_TECHNICAL_PASS_STATE_NOT_CLASSIFIED" if good else "GUEST_ORIGINAL_INPUT_HOLD",
 "original_ZORKDOS_read_only":True,"run_id":run.name,
 "same_pid":M.get("pid"),"same_hwnd":M.get("hwnd"),
 "capture_frames":rows,"metric":diff,
 "debug_trace":str(trace),"debug_trace_status":T.get("status"),
 "source_browser_gameplay_reference":"NONE",
 "game_state_consumption":"VISUAL_REVIEW_REQUIRED",
 "fidelity_verified":False}
out=run/"guest-enter-visual-diagnostic.json"
if out.exists():raise RuntimeError("VISUAL_DIAGNOSTIC_ALREADY_EXISTS")
out.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":r["status"],"frames":rows,"metrics":diff,
"original_game_key_consumed":"UNCLASSIFIED",
"evidence":str(out)},ensure_ascii=False))
raise SystemExit(0 if good else 1)
