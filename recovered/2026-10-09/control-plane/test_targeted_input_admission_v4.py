"""Canary: diagnostic HWND input requires explicitly advertised capability.
Wrong-mode input plans never launch any game or touch a window.
"""
import json,uuid,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[2]
cp=Path(__file__).parent
exe=r/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe"
assert exe.exists()
results=[]
for mode,caps,expected in [
 ("targeted_input_diagnostic",["runtime.fidelity_isolated"],"OWNED_HWND_INPUT_CAPABILITY_REQUIRED"),
 ("passive_diagnostic",["runtime.fidelity_isolated","runtime.passive_capture_diagnostic"],"INPUT_PLAN_FORBIDDEN_OUTSIDE_TARGETED_DIAGNOSTIC"),
 ("strict_fidelity",["runtime.fidelity_isolated"],"INPUT_PLAN_FORBIDDEN_OUTSIDE_TARGETED_DIAGNOSTIC")
]:
 job_id="hwnd-admission-negative-"+uuid.uuid4().hex[:10]
 job={"schema":"ORCH-K003.Job.v1","job_id":job_id,"project":"OpenZork",
      "task":"SafeOwnedInputAdmissionNegative","inputs":[],"required_capabilities":caps,
      "execution":{"kind":"fidelity_runtime","runtime_kind":"dosbox",
          "capture_mode":mode,"executable":str(exe),
          "input_plan":[{"at_seconds":1,"key":"SPACE"}]},
      "validation":{"expected_exit_code":0}}
 src=r/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(job_id+".json")
 src.parent.mkdir(exist_ok=True,parents=True);src.write_text(json.dumps(job,indent=2))
 proc=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(src)],
     capture_output=True,text=True,timeout=20)
 out=r/"runtime-test"/"results"/job_id
 rc=json.loads((out/"control-receipt.json").read_text())
 assert proc.returncode==2 and rc.get("status")=="BLOCKED" and rc.get("reason")==expected,rc
 assert not (out/"result.json").exists() and not (out/"fidelity-isolated").exists()
 results.append({"mode":mode,"reason":rc["reason"],"status":"PASS","runtime_launches":0})
print(json.dumps({"schema":"OpenRemaster.HwndInputAdmissionNegativeCanary.v1","status":"PASS","cases":results}))
