"""Owned HWND diagnostic input through ORCH, never SendInput/focus switching.
Proof is changed pixels on fixture (not merely event posting).
"""
import json,subprocess,sys,uuid
from pathlib import Path
from PIL import Image
from fidelity_runtime_isolation_v1 import gui_conflicts,process_identity,sha256,IsolationError
from fidelity_targeted_input_v1 import validate_plan

def expect(reason,fn):
 try:fn()
 except IsolationError as e:
  assert e.reason==reason,(reason,e.reason);return
 raise AssertionError("Expected fail-closed "+reason)

expect("OWNED_INPUT_PLAN_UNSAFE_EVENT",lambda:validate_plan([{"at_seconds":1,"key":"CTRL_ALT_DEL"}],3))
expect("OWNED_INPUT_PLAN_SIZE_INVALID",lambda:validate_plan([],3))
expect("OWNED_INPUT_PLAN_UNSAFE_EVENT",lambda:validate_plan([{"at_seconds":3,"key":"SPACE"}],3))
root=Path(__file__).resolve().parents[2]
cp=Path(__file__).resolve().parent
exe=root/"work"/"OpenRemaster"/"fidelity_fixture"/"synthetic_scummvm_oracle.exe"
cfg=exe.with_name("scummvm-fixture.ini")
assert exe.is_file() and cfg.is_file()
run_id="fidelity-hwnd-targeted-input-"+uuid.uuid4().hex[:10]
job={
 "schema":"ORCH-K003.Job.v1","job_id":run_id,"project":"OpenRemaster",
 "task":"OwnedWindowKeyboardStateDeltaCanary",
 "inputs":[{"path":str(exe),"sha256":sha256(exe)}],
 "required_capabilities":["runtime.fidelity_isolated","runtime.capture.wgc",
     "runtime.local_capture","input.hwnd_owned_diagnostic"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"targeted_input_diagnostic",
    "runtime_kind":"scummvm","executable":str(exe),"config_source":str(cfg),
    "args":["--config={private_config}","--savepath={private_saves}","--no-fullscreen"],
    "window_title_contains":"OpenRemaster Fixture",
    "input_plan":[{"at_seconds":1,"key":"SPACE"}],
    "capture_backend":"windows_graphics_capture","capture_delay_seconds":3,
    "require_audio":False,"timeout_seconds":20},
 "validation":{"expected_exit_code":0}
}
jobfile=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
jobfile.parent.mkdir(exist_ok=True,parents=True)
jobfile.write_text(json.dumps(job,indent=2),encoding="utf-8")
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
p=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(jobfile)],
      capture_output=True,text=True,timeout=35)
out=root/"runtime-test"/"results"/run_id
a=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
manifest=a.get("capture_evidence",{})
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
colors=[]
if frame.is_file():
 with Image.open(frame) as i:
  img=i.convert("RGB")
  y=img.height//2
  colors=[img.getpixel((img.width//4,y)),img.getpixel((img.width*3//4,y))]
# On target-owned SPACE, fixture becomes green-left and yellow-right.
changed=bool(colors and colors[0][1]>190 and colors[0][0]<70 and
             colors[1][0]>190 and colors[1][1]>190 and colors[1][2]<80)
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
passcondition=(p.returncode==2 and receipt.get("status")=="BLOCKED" and
 a.get("capture_integrity")=="PASS" and a.get("diagnostic_capture_status")=="PASS"
 and a.get("exit_code")==0 and changed and
 len(a.get("owned_input_posted_events",[]))==1 and
 a["owned_input_posted_events"][0].get("global_SendInput_used") is False and
 all(after.get(pid)==ctime for pid,ctime in before.items()))
report={"schema":"OpenRemaster.HwndOwnedInputStateDeltaCanary.v1",
 "status":"PASS" if passcondition else "FAIL","job_id":run_id,
 "sent_key":"SPACE","owned_hwnd":(a.get("runtime_window") or {}).get("hwnd"),
 "receipt_status":receipt.get("status"),"failure_reason":a.get("failure_reason"),
 "diagnostic_capture_status":a.get("diagnostic_capture_status"),
 "frame_colors_left_right":colors,"pixel_state_changed":changed,
 "owned_pid":(a.get("runtime_identity") or {}).get("pid"),
 "other_gui_process_count":len(before),"other_gui_processes_unchanged":sum(after.get(pid)==ctime for pid,ctime in before.items()),
 "fidelity_verified":False,"global_input_used":False,
 "wm_close_sent":a.get("wm_close_sent_to_owned_window"),"result_dir":str(out)}
reportpath=out/"targeted-input-canary.json";reportpath.write_text(json.dumps(report,indent=2))
print(json.dumps(dict(report,evidence=str(reportpath))))
raise SystemExit(0 if passcondition else 1)
