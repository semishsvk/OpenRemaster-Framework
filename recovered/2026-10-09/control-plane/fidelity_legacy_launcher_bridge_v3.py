"""Migrated OpenZork legacy GUI launchers -> ORCH-K003 isolated admission.
Default strict fidelity refuses to launch on occupied GUI, explicit passive diagnostic
is technical-only and cannot grant fidelity acceptance.
"""
import argparse,hashlib,json,subprocess,sys,uuid
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
CONTROL=Path(__file__).resolve().parent
SCUMMVM=ROOT/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
CONFIG=ROOT/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini"
ORCH=CONTROL/"orch_k003.py"
PYTHON=ROOT/"orchestrator"/"native-worker"/"runtime"/"python.exe"

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for x in iter(lambda:f.read(1024*1024),b""):h.update(x)
 return h.hexdigest()

def build_job(task,passive):
 if task not in ("launch-smoke","record-smoke"):
  raise ValueError("UNSUPPORTED_MIGRATED_LAUNCHER")
 if not SCUMMVM.is_file() or not CONFIG.is_file():
  raise FileNotFoundError("OpenZork oracle executable or offline config missing")
 args=["--config={private_config}","--savepath={private_saves}","--no-fullscreen"]
 if task=="launch-smoke":
  args.append("--debuglevel=3")
 else:
  args.extend(["--record-mode=record","--record-file-name={run_dir}\\noinput.rec"])
 args.append("znemesis")
 mode="passive_diagnostic" if passive else "strict_fidelity"
 capabilities=["runtime.fidelity_isolated","runtime.gui_lease.exclusive",
               "runtime.capture.wgc","runtime.local_capture"]
 if task=="launch-smoke":capabilities.append("audio.process_loopback")
 if passive:capabilities.append("runtime.passive_capture_diagnostic")
 run_id="openzork-legacy-"+task+"-"+uuid.uuid4().hex[:10]
 return {
  "schema":"ORCH-K003.Job.v1","job_id":run_id,"project":"OpenZork",
  "task":"LegacyMigrated"+task.replace("-","").title(),
  "inputs":[{"path":str(SCUMMVM),"sha256":sha(SCUMMVM)},
            {"path":str(CONFIG),"sha256":sha(CONFIG)}],
  "required_capabilities":capabilities,
  "execution":{
   "kind":"fidelity_runtime","capture_mode":mode,"runtime_kind":"scummvm",
   "executable":str(SCUMMVM),"config_source":str(CONFIG),"args":args,
   "capture_backend":"windows_graphics_capture",
   "capture_delay_seconds":7 if task=="launch-smoke" else 1,
   "window_title_contains":"Zork Nemesis","require_audio":task=="launch-smoke",
   "audio_duration_ms":3000,"timeout_seconds":30},
  "validation":{"expected_exit_code":0},"acceptance":{"require_validation_pass":True}
 }

def clean_diagnostic_capture(detail,receipt):
 return (detail.get("diagnostic_capture_status")=="PASS"
     and detail.get("capture_integrity")=="PASS" and detail.get("exit_code")==0
     and detail.get("failure_reason")=="DIAGNOSTIC_COMPLETE_NOT_FIDELITY_VERIFIED"
     and receipt.get("status")=="BLOCKED")

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--task",required=True,choices=("launch-smoke","record-smoke"))
 a.add_argument("--passive-diagnostic",action="store_true")
 a.add_argument("--dry-run",action="store_true")
 args=a.parse_args()
 job=build_job(args.task,args.passive_diagnostic)
 jobs=ROOT/"runtime-test"/"jobs"/"legacy-migrated"
 jobs.mkdir(parents=True,exist_ok=True)
 p=jobs/(job["job_id"]+".json")
 p.write_text(json.dumps(job,indent=2),encoding="utf-8")
 if args.dry_run:
  print(json.dumps({"schema":"OpenRemaster.LegacyGUIBridgePlan.v1",
   "status":"PLAN_ONLY_NO_RUNTIME_LAUNCHED","job":job["job_id"],"mode":job["execution"]["capture_mode"],
   "path":str(p),"required_capabilities":job["required_capabilities"]}))
  return 0
 run=subprocess.run([str(PYTHON),"-B",str(ORCH),str(p)],
     capture_output=True,text=True,timeout=60)
 out=ROOT/"runtime-test"/"results"/job["job_id"]
 receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
 detail=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
 technical_pass=clean_diagnostic_capture(detail,receipt)
 report={"schema":"OpenRemaster.LegacyGUIMigratedReceipt.v1",
   "date_utc":datetime.now(timezone.utc).isoformat(),
   "task":args.task,"job_id":job["job_id"],
   "mode":job["execution"]["capture_mode"],
   "status":"TECHNICAL_DIAGNOSTIC_PASS_FIDELITY_HOLD" if technical_pass else receipt.get("status","ERROR"),
   "reason":detail.get("failure_reason",receipt.get("reason","UNKNOWN")),
   "technical_capture_pass":technical_pass,
   "fidelity_accepted":False,
   "original_source_changed":False,
   "orchestrator_return_code":run.returncode,
   "orchestrator_receipt":str(out/"control-receipt.json"),
   "stdout_tail":run.stdout[-350:],"stderr_tail":run.stderr[-450:]}
 report_path=out/"legacy-bridge-report.json"
 out.mkdir(parents=True,exist_ok=True)
 report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(json.dumps(dict(report,report=str(report_path)),ensure_ascii=False))
 if technical_pass and args.passive_diagnostic:
  return 0
 return 2 if receipt.get("status")=="BLOCKED" else 1

if __name__=="__main__":
 try:sys.exit(main())
 except Exception as e:
  print(json.dumps({"status":"ERROR","type":type(e).__name__,"reason":str(e)}))
  sys.exit(3)
