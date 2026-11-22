"""Run synthetic native GUI through full ORCH-K003 supervised passive capture path.
Expected receipt: BLOCKED for fidelity, local diagnostic evidence PASS.
"""
import json,sys,subprocess,uuid
from pathlib import Path
from fidelity_runtime_isolation_v1 import sha256,process_identity,gui_conflicts
root=Path(__file__).resolve().parents[2]
cp=Path(__file__).resolve().parent
exe=root/"work"/"OpenRemaster"/"fidelity_fixture"/"synthetic_scummvm_oracle.exe"
cfg=exe.parent/"scummvm-fixture.ini"
assert exe.is_file() and cfg.is_file()
run_id="fidelity-passive-gui-fixture-"+uuid.uuid4().hex[:10]
job={
 "schema":"ORCH-K003.Job.v1","job_id":run_id,"project":"OpenRemaster","task":"PassiveSyntheticGUIIdentityCanary",
 "inputs":[{"path":str(exe),"sha256":sha256(exe)}],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic","runtime.capture.wgc","runtime.local_capture"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
   "runtime_kind":"scummvm","executable":str(exe),"config_source":str(cfg),
   "args":["--config={private_config}","--savepath={private_saves}","--no-fullscreen"],
   "window_title_contains":"OpenRemaster Fixture",
   "capture_backend":"windows_graphics_capture","require_audio":False,"timeout_seconds":25},
 "validation":{"expected_exit_code":0},"acceptance":{"require_validation_pass":True}
}
jobs=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"
jobs.mkdir(parents=True,exist_ok=True)
jp=jobs/(run_id+".json")
jp.write_text(json.dumps(job,indent=2),encoding="utf-8")
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
p=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(jp)],
                 capture_output=True,text=True,timeout=45)
out=root/"runtime-test"/"results"/run_id
assert (out/"control-receipt.json").is_file(),(p.returncode,p.stderr[-2000:])
receipt=json.loads((out/"control-receipt.json").read_text())
r=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
assert p.returncode==2 and receipt["status"]=="BLOCKED",{"exit":p.returncode,"receipt":receipt,"stderr":p.stderr[-2000:]}
assert r.get("status")=="BLOCKED" and r.get("capture_mode")=="passive_diagnostic",r
assert r.get("diagnostic_capture_status")=="PASS",r
assert r.get("failure_reason")=="DIAGNOSTIC_COMPLETE_NOT_FIDELITY_VERIFIED",r
assert r.get("capture_evidence",{}).get("frames"),r
assert not process_identity(r["runtime_identity"]["pid"]) or process_identity(r["runtime_identity"]["pid"])["creation_ticks_100ns"]!=r["runtime_identity"]["creation_ticks_100ns"],"Owned fixture was not retired"
v=json.loads((out/"validation-result.json").read_text())
assert v["status"]=="FAIL","Diagnostic was accidentally promoted to fidelity PASS"
a=json.loads((out/"acceptance-result.json").read_text())
assert a["status"]=="FAIL","Diagnostic was accidentally promoted to acceptance PASS"
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
original_unmodified=sum(after.get(pid)==ticks for pid,ticks in before.items())
report={"schema":"OpenRemaster.SupervisedPassiveDiagnosticCanary.v1",
        "status":"PASS","job":run_id,
        "diagnostic_capture_status":r["diagnostic_capture_status"],
        "fidelity_admission_status":receipt["status"],
        "fidelity_validator_status":v["status"],
        "capture_manifest_sha256":r["capture_evidence"]["manifest_sha256"],
        "owned_exe_sha256":r["runtime_identity"]["executable_sha256"],
        "owned_pid":r["runtime_identity"]["pid"],
        "owned_hwnd":r["runtime_window"]["hwnd"],
        "foreground_other_gui_snapshot_count":len(before),
        "foreign_gui_processes_unchanged_as_observed":original_unmodified,
        "wm_close_sent":r.get("wm_close_sent_to_owned_window"),
        "no_original_runtime_fidelity_claim":True,
        "receipt":str(out/"control-receipt.json")}
dest=out/"diagnostic-summary.json"
dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(dest)),ensure_ascii=False))
