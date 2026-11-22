"""Fail-closed mouse authority tests; no new runtime may start."""
import json,subprocess,sys,uuid
from pathlib import Path
from fidelity_targeted_input_v1 import validate_plan
from fidelity_runtime_isolation_v1 import IsolationError

ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
EXE=ROOT/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe"
assert EXE.is_file()

def expect(reason,call):
 try:call()
 except IsolationError as e:
  assert e.reason==reason,(e.reason,reason);return
 raise AssertionError("FAIL_OPEN_EXPECTED "+reason)
expect("OWNED_INPUT_PLAN_EVENT_INVALID",lambda:validate_plan([{
 "at_seconds":1,"action":"MOUSE_LEFT_CLICK","client_x":90,"client_y":90,
 "host_global_screen_x":900}],4))
expect("OWNED_INPUT_PLAN_MOUSE_COORDINATE_INVALID",lambda:validate_plan([{
 "at_seconds":1,"action":"MOUSE_LEFT_CLICK","client_x":True,"client_y":90}],4))
expect("OWNED_INPUT_PLAN_UNSAFE_EVENT",lambda:validate_plan([{
 "at_seconds":6,"action":"MOUSE_LEFT_CLICK","client_x":90,"client_y":90}],4))
checks=[
 ("targeted_input_diagnostic",["runtime.fidelity_isolated","input.hwnd_owned_diagnostic"],
  "OWNED_MOUSE_CAPABILITY_REQUIRED"),
 ("passive_diagnostic",["runtime.fidelity_isolated","runtime.passive_capture_diagnostic","input.hwnd_owned_mouse_diagnostic"],
  "INPUT_PLAN_FORBIDDEN_OUTSIDE_TARGETED_DIAGNOSTIC"),
 ("strict_fidelity",["runtime.fidelity_isolated","input.hwnd_owned_mouse_diagnostic"],
  "INPUT_PLAN_FORBIDDEN_OUTSIDE_TARGETED_DIAGNOSTIC")
]
output=[]
for mode,caps,reason in checks:
 job_id="owned-mouse-guard-"+uuid.uuid4().hex[:10]
 job={"schema":"ORCH-K003.Job.v1","job_id":job_id,
      "project":"OpenRemaster","task":"MouseAdmissionNegative",
      "inputs":[],"required_capabilities":caps,
      "execution":{"kind":"fidelity_runtime","capture_mode":mode,
        "runtime_kind":"dosbox","executable":str(EXE),
        "input_plan":[{"at_seconds":1,"action":"MOUSE_LEFT_CLICK","client_x":90,"client_y":90}]},
      "validation":{"expected_exit_code":0}}
 jp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(job_id+".json")
 jp.parent.mkdir(parents=True,exist_ok=True)
 jp.write_text(json.dumps(job,indent=2))
 r=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jp)],
                  text=True,capture_output=True,timeout=12)
 results=ROOT/"runtime-test"/"results"/job_id
 rc=json.loads((results/"control-receipt.json").read_text())
 assert r.returncode==2 and rc["status"]=="BLOCKED" and rc["reason"]==reason,(mode,rc)
 assert not (results/"result.json").exists()
 output.append({"mode":mode,"reason":reason,"original_game_launches":0})
print(json.dumps({"schema":"OpenRemaster.OwnedMouseAdmissionCanary.v1",
"status":"PASS","cases":output,"host_global_mouse_actions":0}))
