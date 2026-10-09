"""Bounded owned-client mouse click on Zork Nemesis New Game title option.
Posts ONLY to exact DOSBox-X PID/HWND, never to global cursor or desktop.
No game-state claim until the final native framebuffer is inspected.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess,sys,uuid
from PIL import Image
import numpy as np
from fidelity_runtime_isolation_v1 import gui_conflicts,sha256
ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
job_src=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/"openzork-dosboxx-threepoint-c0b9fda589.json"
assert job_src.is_file()
template=json.loads(job_src.read_text(encoding="utf-8"))
run_id="openzork-newgame-owned-mouse-"+uuid.uuid4().hex[:9]
template["job_id"]=run_id
template["task"]="OriginalDOSBoxXOwnedMouseMenuStateProbe"
exec_job=template["execution"]
exec_job["capture_mode"]="targeted_input_diagnostic"
exec_job.pop("capture_schedule_seconds",None)
exec_job["capture_delay_seconds"]=44
exec_job["input_plan"]=[
  {"at_seconds":40,"action":"MOUSE_LEFT_CLICK","client_x":215,"client_y":235}
]
exec_job["timeout_seconds"]=72
exec_job["require_audio"]=False
template["required_capabilities"]=[
  "runtime.fidelity_isolated","runtime.gui_lease.exclusive","runtime.capture.wgc",
  "runtime.local_capture","input.hwnd_owned_diagnostic","input.hwnd_owned_mouse_diagnostic"
]
inp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
inp.write_text(json.dumps(template,indent=2),encoding="utf-8")
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(inp)],
                    capture_output=True,text=True,timeout=95)
out=ROOT/"runtime-test"/"results"/run_id
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
r=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
v=json.loads((out/"validation-result.json").read_text()) if (out/"validation-result.json").is_file() else {}
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
base=ROOT/"runtime-test"/"results"/"openzork-dosboxx-threepoint-c0b9fda589"/"fidelity-isolated"/"capture"/"samples"/"point-03"/"frame-0001.bmp"
frame_details={}
if frame.is_file():
 with Image.open(frame) as src:
  img=src.convert("RGB")
  img.save(frame.with_suffix(".png"))
  a=np.asarray(img,dtype=np.int16)
  frame_details.update({"size":[img.width,img.height],
                         "mean_rgb":list(a.mean(axis=(0,1)).round(2)),
                         "stddev_rgb":list(a.std(axis=(0,1)).round(2))})
 base=ROOT/"runtime-test"/"results"/"openzork-dosboxx-threepoint-c0b9fda589"/"fidelity-isolated"/"capture"/"samples"/"point-03"/"frame-0001.bmp"
 with Image.open(base) as old:
  b=np.asarray(old.convert("RGB"),dtype=np.int16)
 if b.shape==a.shape:
  delta=np.abs(a[73:]-b[73:])
  frame_details["fraction_pixel_changed_vs_original_title"]=round(float(np.mean(np.any(delta>25,axis=2))),6)
  frame_details["mae_vs_original_title"]=round(float(delta.mean()),3)
else:frame_details["status"]="NO_FRAME"
events=r.get("owned_input_posted_events") or []
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
pass_tech=(proc.returncode==2 and receipt.get("status")=="BLOCKED"
 and v.get("status")=="FAIL"
 and r.get("diagnostic_capture_status")=="PASS"
 and r.get("exit_code")==0 and frame.is_file()
 and len(events)==1 and events[0].get("action")=="MOUSE_LEFT_CLICK"
 and events[0].get("global_SetCursorPos_used") is False
 and events[0].get("focus_switched") is False
 and all(after.get(pid)==ctime for pid,ctime in before.items()))
report={
"schema":"OpenZork.OriginalDOSBoxXOwnedMouseNewGameDiagnostic.v1",
"status":"INPUT_DELIVERY_AND_CAPTURE_TECHNICAL_PASS_STATE_REVIEW_REQUIRED" if pass_tech else "BLOCKED",
"timestamp_utc":datetime.now(timezone.utc).isoformat(),
"run_id":run_id,"input_claim":"WM_MOUSEMOVE_AND_LBUTTON_ON_OWNED_HWND_ONLY",
"click_client":[215,235],"posted_at_offset_seconds":40,
"capture_at_offset_seconds":44,
"event_receipts":events,
"original_title_reference_sha256":sha256(base),
"capture_sha256":sha256(frame) if frame.is_file() else None,
"manifest_sha256":(r.get("capture_evidence") or {}).get("manifest_sha256"),
"runtime_exit":r.get("exit_code"),
"post_image":str(frame.with_suffix(".png")) if frame.is_file() else None,
"image_measurements":frame_details,
"failure_reason":r.get("failure_reason"),
"all_21_foreign_gui_processes_preserved":sum(after.get(pid)==ctime for pid,ctime in before.items()),
"fidelity_verified":False,"new_game_selected":"UNVERIFIED_VISUAL_INSPECTION_NEEDED"
}
out.mkdir(parents=True,exist_ok=True)
dest=out/"owned-mouse-state-probe.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"run_id":run_id,
                  "runtime_exit":report["runtime_exit"],
                  "image":report["post_image"],
                  "measurements":frame_details,
                  "foreign_pids_preserved":report["all_21_foreign_gui_processes_preserved"],
                  "evidence":str(dest)},ensure_ascii=False))
raise SystemExit(0 if pass_tech else 1)
