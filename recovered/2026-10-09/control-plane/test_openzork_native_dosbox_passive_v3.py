"""First supervised DOSBox ZORKDOS.EXE original execution. Diagnostic only.
Single owner process, read-only original Zork Nemesis corpus, per-run overlay/capture.
"""
import json,sys,subprocess,uuid
from pathlib import Path
from datetime import datetime,timezone
from fidelity_runtime_isolation_v1 import sha256,process_identity,gui_conflicts
ROOT=Path(__file__).resolve().parents[2]; CP=Path(__file__).resolve().parent
exe=ROOT/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe"
seed=CP/"examples"/"OpenZork-dosbox-fidelity-seed.conf"
assert exe.is_file() and seed.is_file()
run_id="openzork-native-dosbox-passive-"+uuid.uuid4().hex[:9]
job={
 "schema":"ORCH-K003.Job.v1","job_id":run_id,"project":"OpenZork",
 "task":"OriginalZORKDOSNativeDOSBoxPassiveDiagnostic",
 "inputs":[{"path":str(exe),"sha256":sha256(exe)},{"path":str(seed),"sha256":sha256(seed)}],
 "required_capabilities":["runtime.fidelity_isolated","runtime.gui_lease.exclusive","runtime.local_capture",
                          "runtime.capture.wgc","runtime.passive_capture_diagnostic"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
 "runtime_kind":"dosbox","executable":str(exe),"config_source":str(seed),
 "args":["-conf","{private_config}","-noconsole"],
 "window_title_contains":"DOSBox","capture_backend":"windows_graphics_capture",
 "capture_delay_seconds":7,"require_audio":False,"timeout_seconds":27},
 "validation":{"expected_exit_code":0},"acceptance":{"require_validation_pass":True}
}
jp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
jp.parent.mkdir(parents=True,exist_ok=True);jp.write_text(json.dumps(job,indent=2),encoding="utf-8")
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
p=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jp)],
                 capture_output=True,text=True,timeout=55)
out=ROOT/"runtime-test"/"results"/run_id
rc=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
r=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
v=json.loads((out/"validation-result.json").read_text()) if (out/"validation-result.json").exists() else {}
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
passed=(p.returncode==2 and rc.get("status")=="BLOCKED" and r.get("diagnostic_capture_status")=="PASS"
       and r.get("capture_integrity")=="PASS" and r.get("exit_code")==0
       and bool(r.get("capture_evidence",{}).get("frames")) and v.get("status")=="FAIL")
report={"schema":"OpenZork.NativeDOSBoxSupervisedPassiveDiagnostic.v1",
        "status":"PASS_DIAGNOSTIC" if passed else "BLOCKED",
        "run_id":run_id,"timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "runtime_executable":str(exe),"executable_sha256":sha256(exe),
        "source_readonly":True,"private_overlay":True,
        "worker_result_status":r.get("status"),"runtime_exit":r.get("exit_code"),
        "reason":r.get("failure_reason"),"diagnostic_capture_status":r.get("diagnostic_capture_status"),
        "local_video_sha256":(r.get("capture_evidence",{}).get("frames") or [{}])[0].get("sha256"),
        "capture_manifest_sha256":r.get("capture_evidence",{}).get("manifest_sha256"),
        "process_identity":r.get("runtime_identity"),
        "window":r.get("runtime_window"),"read_only_native_game_fidelity":"NOT_VERIFIED",
        "fidelity_validation_status":v.get("status"),
        "other_gui_processes_before":len(before),
        "other_gui_processes_preserved":sum(after.get(k)==v for k,v in before.items()),
        "stdout_tail":p.stdout[-380:],"stderr_tail":p.stderr[-400:],
        "result_dir":str(out)}
report_path=out/"native-dosbox-passive-diagnostic.json"
out.mkdir(parents=True,exist_ok=True)
report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(report_path)),ensure_ascii=False))
raise SystemExit(0 if passed else 1)
