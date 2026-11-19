"""Negative ORCH-K003 audio admission test. Must never start a runtime."""
import json,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
run_id="audio-capability-canary-"+uuid.uuid4().hex[:10]
job={
 "schema":"ORCH-K003.Job.v1","job_id":run_id,"project":"OpenZork","task":"NegativeAudioCapabilityProbe",
 "inputs":[],"required_capabilities":["runtime.fidelity_isolated","runtime.local_capture"],
 "execution":{"kind":"fidelity_runtime","runtime_kind":"scummvm",
  "executable":str(ROOT/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"),
  "args":[],"require_audio":True},
 "validation":{"expected_exit_code":0}}
inp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
inp.parent.mkdir(exist_ok=True,parents=True)
inp.write_text(json.dumps(job,indent=2))
p=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(inp)],capture_output=True,text=True,timeout=20)
out=ROOT/"runtime-test"/"results"/run_id
receipt=json.loads((out/"control-receipt.json").read_text())
assert p.returncode==2 and receipt["status"]=="BLOCKED" and receipt["reason"]=="PROCESS_LOOPBACK_CAPABILITY_REQUIRED",(p.returncode,receipt)
assert not (out/"result.json").exists() and not (out/"fidelity-isolated").exists()
caps=json.loads((CP/"capabilities.json").read_text())["workers"]
assert "audio.process_loopback" in next(w for w in caps if w["worker_id"]=="HomePC-GodotRuntimeWorker")["capabilities"]
assert "audio.process_loopback" not in next(w for w in caps if w["worker_id"]=="HomePC-NativeWorker")["capabilities"]
print(json.dumps({"schema":"FidelityAudioCapabilityNegativeCanary.v1","status":"PASS",
                  "audio_missing_capability":"BLOCKED","session_0_not_audio_routable":True,
                  "runtime_launch_count":0,"job":run_id}))
