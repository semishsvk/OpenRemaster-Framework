"""Independent original ZORKDOS owned DOSBox-X debugger mouse-move timeline analysis.
Compares two real local WGC frames from SAME process, with no fidelity acceptance.
"""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw
import numpy as np
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-original-dosboxx-native-mcp-mousemove-20261009-r1"
capture=run/"fidelity-isolated"/"capture"
tracefile=run/"debugger-mousemove-trace.json"
resultfile=run/"result.json"
masterfile=capture/"capture-attestation.json"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
trace=json.loads(tracefile.read_text(encoding="utf-8")) if tracefile.is_file() else {}
result=json.loads(resultfile.read_text(encoding="utf-8")) if resultfile.is_file() else {}
master=json.loads(masterfile.read_text(encoding="utf-8")) if masterfile.is_file() else {}
verify=None;frames=[];metric={}
if master:
 try:verify=verify_bounded_wgc_sequence(capture,master)
 except Exception as e:metric["verify_error"]=type(e).__name__+":"+str(e)
 if len(master.get("frames") or [])==2:
  for row in master["frames"]:
   path=capture/row["path"]
   with Image.open(path) as img:
    frame=img.convert("RGB")
    outfile=path.with_suffix(".png")
    frame.save(outfile)
    frames.append({"path":str(outfile),"array":np.asarray(frame,dtype=np.int16),
     "size":frame.size,"sha256":row["sha256"],"at":row["requested_at_seconds"]})
  if frames[0]["array"].shape==frames[1]["array"].shape:
   A=frames[0]["array"];B=frames[1]["array"]
   delta=np.abs(A-B)
   changed=np.any(delta>25,axis=2)
   y,x=np.where(changed)
   metric={
    "shape":list(A.shape),"raw_MAE":round(float(delta.mean()),4),
    "changed_pixel_fraction_gt25":round(float(changed.mean()),7),
    "changed_pixel_count_gt25":int(changed.sum()),
    "difference_bbox_xyxy":([int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
                             if len(x) else None),
    "frame_SHA256_identical":frames[0]["sha256"]==frames[1]["sha256"]}
   diff=Image.fromarray(delta.clip(0,255).astype(np.uint8),"RGB")
   diffpath=run/"mouse-move-absolute-diff.png"
   diff.save(diffpath)
   contact=Image.new("RGB",(max(1300,A.shape[1]*2),A.shape[0]+90),(12,12,12))
   contact.paste(Image.fromarray(A.astype(np.uint8),"RGB"),(5,50))
   contact.paste(Image.fromarray(B.astype(np.uint8),"RGB"),(A.shape[1]+12,50))
   draw=ImageDraw.Draw(contact)
   draw.text((10,12),"DOSBox-X native ZORKDOS before emulated mouse Y motion",fill="white")
   draw.text((A.shape[1]+12,12),"same PID/HWND after integration-device motion",fill="white")
   contactpath=run/"native-mouse-movement-before-after.png"
   contact.save(contactpath)
   metric["difference_png"]=str(diffpath)
   metric["contact_sheet"]=str(contactpath)
safe=(
 result.get("diagnostic_capture_status")=="PASS"
 and result.get("exit_code")==0
 and len(frames)==2
 and trace.get("status")=="MCP_INTERNAL_MOUSE_MOVE_ISSUED_NO_GAME_CONSUMPTION_PROOF"
 and trace.get("integration_identification_verified") is True
 and verify and verify.get("status")=="PASS_TECHNICAL_CAPTURE_ONLY"
 and master.get("pid")==result.get("runtime_identity",{}).get("pid")
)
report={
 "schema":"OpenZork.NativeDOSBoxXIntegrationMouseMovementStateProbe.v1",
 "status":"MCP_MOUSE_EVENT_AND_LOCAL_FRAMES_TECHNICAL_PASS_VISUAL_STATE_UNVERIFIED" if safe else "MCP_NATIVE_INPUT_AND_CAPTURE_HOLD",
 "run_id":run.name,
 "source_original_ZORKDOS_in_DOSBoxX":True,
 "integration_debugger_trace_sha256":sha(tracefile) if tracefile.is_file() else None,
 "registered_emulator_sha256":(result.get("registered_target") or {}).get("executable_sha256"),
 "game_source_binding":result.get("game_source_binding"),
 "owner_pid":master.get("pid"),"owner_hwnd":master.get("hwnd"),
 "command_delivery":"MCP_OUTD_GUEST_INTEGRATION_PORTS_ONLY",
 "global_windows_mouse_used":False,
 "frame_1":{k:v for k,v in frames[0].items() if k!="array"} if len(frames)>=1 else {},
 "frame_2":{k:v for k,v in frames[1].items() if k!="array"} if len(frames)>=2 else {},
 "metrics":metric,
 "runtime_exit":result.get("exit_code"),
 "debugger_source_attribution":"NOT_PID_ATTESTED_BEYOND_LOCAL_CONFIG_AND_PORT",
 "guest_mouse_motion_consumption":"NOT_YET_CLASSIFIED_BY_VISUAL_EVIDENCE",
 "original_vs_reconstruction_fidelity":"NOT_TESTED",
 "source_corpus_modified":False}
out=run/"native-mcp-mousemove-technical-analysis.json"
if out.exists():raise RuntimeError("ANALYSIS_ALREADY_EXISTS")
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"run_id":run.name,
 "runtime_exit":report["runtime_exit"],"metric":metric,
 "trace_status":trace.get("status"),"original_game_input_consumed":"UNVERIFIED",
 "analysis":str(out)},ensure_ascii=False))
raise SystemExit(0 if safe else 1)
