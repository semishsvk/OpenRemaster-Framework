"""Isolated Win32 mouse fixture; validates client-only WM_MOUSEMOVE/LBUTTONDOWN/UP.
Captures visual state change and proves no global desktop cursor/focus control.
"""
import json,subprocess,sys,uuid
from pathlib import Path
from PIL import Image
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts,IsolationError
from fidelity_targeted_input_v1 import validate_plan

def expect_fail(reason,cb):
 try:cb()
 except IsolationError as e:
  assert e.reason==reason,(reason,e.reason);return
 raise AssertionError("Expected "+reason)

expect_fail("OWNED_INPUT_PLAN_UNSAFE_EVENT",
  lambda:validate_plan([{"at_seconds":1,"action":"MOUSE_RIGHT_CLICK","client_x":180,"client_y":150}],3))
expect_fail("OWNED_INPUT_PLAN_MOUSE_COORDINATE_INVALID",
  lambda:validate_plan([{"at_seconds":1,"action":"MOUSE_LEFT_CLICK","client_x":-1,"client_y":150}],3))
assert validate_plan([{"at_seconds":1,"action":"MOUSE_LEFT_CLICK","client_x":180,"client_y":150}],3)
r=Path(__file__).resolve().parents[2];cp=Path(__file__).resolve().parent
exe=r/"work"/"OpenRemaster"/"fidelity_fixture"/"synthetic_scummvm_oracle.exe"
cfg=exe.parent/"scummvm-fixture.ini"
rid="fidelity-mouse-owned-"+uuid.uuid4().hex[:9]
job={"schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenRemaster",
"task":"MouseHwndOwnershipSyntheticCanary","inputs":[{"path":str(exe),"sha256":sha256(exe)}],
"required_capabilities":["runtime.fidelity_isolated","input.hwnd_owned_diagnostic",
                         "input.hwnd_owned_mouse_diagnostic","runtime.capture.wgc","runtime.local_capture"],
"execution":{"kind":"fidelity_runtime","capture_mode":"targeted_input_diagnostic",
             "runtime_kind":"scummvm","executable":str(exe),"config_source":str(cfg),
             "args":["--config={private_config}","--savepath={private_saves}","--no-fullscreen"],
             "window_title_contains":"OpenRemaster Fixture",
             "input_plan":[{"at_seconds":1.0,"action":"MOUSE_LEFT_CLICK","client_x":180,"client_y":150}],
             "capture_delay_seconds":3,"require_audio":False,"timeout_seconds":20,
             "capture_backend":"windows_graphics_capture"},
"validation":{"expected_exit_code":0}}
jp=r/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(rid+".json")
jp.parent.mkdir(exist_ok=True,parents=True);jp.write_text(json.dumps(job,indent=2))
foreign={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(jp)],
                    capture_output=True,text=True,timeout=35)
out=r/"runtime-test"/"results"/rid
result=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
rc=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
pixels=[]
if frame.is_file():
 with Image.open(frame) as image:
  im=image.convert("RGB");pixels=[im.getpixel((im.width//4,im.height//2)),
                                  im.getpixel((3*im.width//4,im.height//2))]
expected=bool(pixels and pixels[0][1]>200 and pixels[0][0]<50 and
              pixels[1][0]>200 and pixels[1][1]>200 and pixels[1][2]<50)
acts=result.get("owned_input_posted_events") or []
new={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
passed=(proc.returncode==2 and rc.get("status")=="BLOCKED" and
 result.get("diagnostic_capture_status")=="PASS" and result.get("exit_code")==0
 and len(acts)==1 and acts[0].get("action")=="MOUSE_LEFT_CLICK"
 and acts[0].get("global_SetCursorPos_used") is False
 and acts[0].get("global_SendInput_used") is False
 and acts[0].get("focus_switched") is False
 and expected and all(new.get(k)==v for k,v in foreign.items()))
evidence={"schema":"OpenRemaster.OwnedMouseStateDeltaSyntheticCanary.v1",
"status":"PASS" if passed else "FAIL",
"job_id":rid,"state_delta_colors":pixels,
"original_red_blue_to_green_yellow":expected,
"click_client_xy":[180,150],
"original_game_mouse_consumption":"NOT_TESTED",
"fidelity_status":"NOT_VERIFIED",
"foreign_GUI_unchanged":sum(new.get(k)==v for k,v in foreign.items()),
"global_mouse_moved":False,
"worker_runtime_exit":result.get("exit_code"),
"technical_capture_sha256":(result.get("capture_evidence") or {}).get("manifest_sha256"),
"receipt":str(out/"control-receipt.json")}
dest=out/"mouse-canary.json";out.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(evidence,indent=2),encoding="utf-8")
print(json.dumps(dict(evidence,evidence_path=str(dest))))
raise SystemExit(0 if passed else 1)
