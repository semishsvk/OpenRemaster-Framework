"""First real ZORKDOS native emulator mouse movement: observable image state after command.
Frame-time provenance and debugger trace do not by themselves prove a guest interaction.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-live-mousemove-20261009-r4"
base=R/"runtime-test"/"results"/rid
capture=base/"fidelity-isolated"/"capture"
manifest=capture/"capture-attestation.json"
report=base/"normal-run-emulated-mouse-motion-analysis.json"
if report.exists():raise RuntimeError("MOUSE_MOTION_ANALYSIS_ALREADY_EXISTS")
m=json.loads(manifest.read_text(encoding="utf-8-sig"))
assert verify_bounded_wgc_sequence(capture,m)["status"]=="PASS_TECHNICAL_CAPTURE_ONLY"
trace=json.loads((base/"MCP-live-guest-movement-trace.json").read_text(encoding="utf-8-sig"))
worker=json.loads((base/"result.json").read_text(encoding="utf-8-sig"))
assert len(m["frames"])==2 and [x["requested_at_seconds"] for x in m["frames"]]==[39,44]
assert m["pid"]==worker["runtime_identity"]["pid"] and m["hwnd"]==worker["runtime_window"]["hwnd"]
frames=[];images=[]
for row in m["frames"]:
 path=capture/row["path"]
 with Image.open(path) as image:
  im=image.convert("RGB")
  png=path.with_suffix(".png")
  im.save(png)
  frames.append({"time":row["requested_at_seconds"],"sha256":row["sha256"],
                 "path":str(png),"width":im.width,"height":im.height})
  images.append(np.asarray(im,dtype=np.uint8))
comparison={}
if images[0].shape==images[1].shape:
 a=images[0].astype(np.int16);b=images[1].astype(np.int16)
 diff=np.abs(a-b)
 comparison={"MAE":round(float(diff.mean()),5),
 "pixel_gt_20_fraction":round(float(np.any(diff>20,axis=2).mean()),6),
 "frame_hashes_equal":frames[0]["sha256"]==frames[1]["sha256"]}
 dt=Image.fromarray(diff.clip(0,255).astype(np.uint8),"RGB")
 dt.save(base/"native-emulated-mouse-absolute-diff.png")
 side=Image.new("RGB",(a.shape[1]*2+24,a.shape[0]+64),(12,12,12))
 pen=ImageDraw.Draw(side)
 side.paste(Image.fromarray(images[0],"RGB"),(8,38))
 side.paste(Image.fromarray(images[1],"RGB"),(a.shape[1]+16,38))
 pen.text((8,10),"native original ZORKDOS before guest mouse movement (39s)",fill="white")
 pen.text((a.shape[1]+16,10),"same owned PID/HWND after guest mouse movement (44s)",fill="white")
 side.save(base/"native-move-before-after-timeline.png")
 comparison["contact_sheet"]=str(base/"native-move-before-after-timeline.png")
 elseone=0
report_data={
 "schema":"OpenZork.NativeZORKDOSLiveGuestMouseMovementObservation.v1",
 "status":"LOCAL_ORIGINAL_FRAMES_AND_MCP_INTERNAL_INPUT_RECORDED_VISUAL_CONSUMPTION_NOT_YET_VERIFIED",
 "original_ZORKDOS_exec":"READ_ONLY_NATIVE",
 "emulator_kind":"DOSBOX_X_2026_10_01",
 "run_id":rid,"emulator_PID":m["pid"],"WGC_HWND":m["hwnd"],
 "frames":frames,"comparison":comparison,
 "debugger_command_receipt_sha256":hashlib.sha256((base/"MCP-live-guest-movement-trace.json").read_bytes()).hexdigest(),
 "debugger_trace_status":trace["status"],
 "no_debugger_halt":trace["debugger_halted_guest"] is False,
 "debugger_input_event":"emulator_internal_relative_mouse_y_110",
 "global_windows_mouse_used":False,
 "gameplay_control_consumed":"UNVERIFIED_REQUIRES_VISUAL_INSPECTION",
 "original_vs_reconstruction_fidelity":"NOT_PERFORMED"
}
report.write_text(json.dumps(report_data,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report_data["status"],"images":frames,
"metrics":comparison,"trace":report_data["debugger_trace_status"],
"evidence":str(report)},ensure_ascii=False))
