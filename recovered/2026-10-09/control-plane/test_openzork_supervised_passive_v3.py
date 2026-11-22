"""Supervised genuine Zork Nemesis ScummVM passive original-runtime diagnostic.
No input, no fidelity promotion, no mutation of original game corpus.
"""
from datetime import datetime,timezone
import json,sys,subprocess,uuid
from pathlib import Path
from fidelity_runtime_isolation_v1 import gui_conflicts,process_identity,sha256
root=Path(__file__).resolve().parents[2]
cp=Path(__file__).resolve().parent
exe=root/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
cfg=root/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini"
assert exe.is_file() and cfg.is_file()
run_id="openzork-supervised-oracle-passive-"+uuid.uuid4().hex[:9]
job={
 "schema":"ORCH-K003.Job.v1","job_id":run_id,"project":"OpenZork",
 "task":"OriginalRuntimeSupervisedVideoAudioDiagnostic",
 "inputs":[{"path":str(exe),"sha256":sha256(exe)},{"path":str(cfg),"sha256":sha256(cfg)}],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
                          "runtime.capture.wgc","runtime.local_capture","audio.process_loopback"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
    "runtime_kind":"scummvm","executable":str(exe),"config_source":str(cfg),
    "args":["--config={private_config}","--savepath={private_saves}","--no-fullscreen","znemesis"],
    "window_title_contains":"Zork Nemesis",
    "capture_backend":"windows_graphics_capture","capture_delay_seconds":7,
    "require_audio":True,"audio_duration_ms":3000,"timeout_seconds":25},
 "validation":{"expected_exit_code":0},"acceptance":{"require_validation_pass":True}
}
jobs=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"
jobs.mkdir(exist_ok=True,parents=True)
jp=jobs/(run_id+".json")
jp.write_text(json.dumps(job,indent=2),encoding="utf-8")
foreign_before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
r=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(jp)],capture_output=True,text=True,timeout=60)
out=root/"runtime-test"/"results"/run_id
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
result=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
validated=json.loads((out/"validation-result.json").read_text()) if (out/"validation-result.json").exists() else {}
actual_result={"schema":"OpenZork.SupervisedOriginalPassiveDiagnostic.v1",
  "date_utc":datetime.now(timezone.utc).isoformat(),"status":"PASS" if
   (r.returncode==2 and receipt.get("status")=="BLOCKED" and
    result.get("diagnostic_capture_status")=="PASS" and
    result.get("capture_evidence",{}).get("audio") and
    validated.get("status")=="FAIL" and result.get("capture_mode")=="passive_diagnostic")
    else "FAIL",
  "process_exit":r.returncode,"original_runtime_fidelity":"NOT_VERIFIED",
  "receipt_status":receipt.get("status"),"reason":result.get("failure_reason"),
  "diagnostic_status":result.get("diagnostic_capture_status"),
  "validation_status":validated.get("status"),
  "capture_sha256":result.get("capture_evidence",{}).get("manifest_sha256"),
  "video_sha256":(result.get("capture_evidence",{}).get("frames") or [{}])[0].get("sha256"),
  "audio_sha256":(result.get("capture_evidence",{}).get("audio") or [{}])[0].get("sha256"),
  "runtime_identity":result.get("runtime_identity"),
  "runtime_window":result.get("runtime_window"),
  "stdout_tail":r.stdout[-450:],"stderr_tail":r.stderr[-450:],
  "foreign_gui_before":len(foreign_before),
  "artifacts":str(out)}
foreign_after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
actual_result["unaffected_prior_gui_processes_observed"]=sum(foreign_after.get(pid)==start for pid,start in foreign_before.items())
target=out/"supervised-diagnostic-summary.json"
target.write_text(json.dumps(actual_result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(dict(actual_result,evidence=str(target)),ensure_ascii=False))
raise SystemExit(0 if actual_result["status"]=="PASS" else 1)
