import argparse,datetime,hashlib,json,subprocess,sys
from pathlib import Path
from execution_journal import append_event
from validator import validate
from acceptance import accept
from idempotency import operation_id, reconcile
from leases import acquire, release
from fidelity_runtime_worker_v1 import run as run_fidelity_runtime
from fidelity_legacy_executable_guard_v1 import check_executable_runtime
ROOT=Path(__file__).resolve().parent; FRAMEWORK=ROOT.parent.parent
CAPS=json.loads((ROOT/"capabilities.json").read_text(encoding="utf-8"))
COMMISSIONING=json.loads((ROOT/"worker-commissioning.json").read_text(encoding="utf-8"))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def route(req):
 need=set(req); c=[w for w in CAPS["workers"] if w.get("enabled") and COMMISSIONING.get("workers",{}).get(w["worker_id"],{}).get("routable",False) and need.issubset(set(w.get("capabilities",[])))]
 return sorted(c,key=lambda x:(x.get("adapter")!="NativeLocalQueue",x["worker_id"]))[0] if c else None
def main():
 ap=argparse.ArgumentParser();ap.add_argument("job");a=ap.parse_args();jp=Path(a.job);job=json.loads(jp.read_text(encoding="utf-8-sig"))
 if job.get("schema")!="ORCH-K003.Job.v1":raise ValueError("unsupported control job")
 out=FRAMEWORK/"runtime-test"/"results"/job["job_id"];out.mkdir(parents=True,exist_ok=True)
 pre=job.get("execution",{})
 if pre.get("kind")=="godot_runtime" and pre.get("mode","replay") not in ("smoke","headless","replay","import"):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"GODOT_GUI_MODE_REQUIRES_FIDELITY_RUNTIME_SUPERVISOR"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="executable_runtime":
  name=Path(pre.get("executable","")).name.lower()
  if pre.get("interactive") or pre.get("requires_gui") or name.startswith(("dosbox","scummvm","retroarch")) or (name.startswith("godot") and "--headless" not in pre.get("args",[])):
   blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"INTERACTIVE_GUI_REQUIRES_FIDELITY_RUNTIME_SUPERVISOR"}
   (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
   print(json.dumps(blocked));return 2
  unsafe=check_executable_runtime(pre)
  if unsafe:
   blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],
            "status":"BLOCKED","reason":unsafe["reason"],"admission_evidence":unsafe}
   (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
   print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and pre.get("seed_saves") is not None and "runtime.saved_state_seed.copy" not in job.get("required_capabilities",[]):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"READ_ONLY_SAVE_SEED_CAPABILITY_REQUIRED"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and pre.get("capture_schedule_seconds") is not None and pre.get("capture_mode","strict_fidelity")!="passive_diagnostic":
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"CAPTURE_SEQUENCE_REQUIRES_PASSIVE_DIAGNOSTIC"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and any(
    isinstance(e,dict) and e.get("action")=="MOUSE_LEFT_CLICK"
    for e in (pre.get("input_plan") or [])
 ) and "input.hwnd_owned_mouse_diagnostic" not in job.get("required_capabilities",[]):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"OWNED_MOUSE_CAPABILITY_REQUIRED"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and pre.get("capture_mode")=="targeted_input_diagnostic" and "input.hwnd_owned_diagnostic" not in job.get("required_capabilities",[]):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"OWNED_HWND_INPUT_CAPABILITY_REQUIRED"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and pre.get("input_plan") and pre.get("capture_mode")!="targeted_input_diagnostic":
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"INPUT_PLAN_FORBIDDEN_OUTSIDE_TARGETED_DIAGNOSTIC"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and pre.get("capture_mode","strict_fidelity")=="passive_diagnostic" and "runtime.passive_capture_diagnostic" not in job.get("required_capabilities",[]):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"PASSIVE_DIAGNOSTIC_CAPABILITY_REQUIRED"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and pre.get("require_audio") and "audio.process_loopback" not in job.get("required_capabilities",[]):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"PROCESS_LOOPBACK_CAPABILITY_REQUIRED"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 if pre.get("kind")=="fidelity_runtime" and "runtime.fidelity_isolated" not in job.get("required_capabilities",[]):
  blocked={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"status":"BLOCKED","reason":"FIDELITY_ISOLATION_CAPABILITY_REQUIRED"}
  (out/"control-receipt.json").write_text(json.dumps(blocked,indent=2),encoding="utf-8")
  print(json.dumps(blocked));return 2
 journal=out/"execution-journal.jsonl"
 append_event(journal,job["job_id"],"JOB_CREATED",lifecycle="CREATED",project=job["project"],task=job["task"],control_job_sha256=sha(jp))
 receipt={"schema":"ORCH-K003.ExecutionReceipt.v1","job_id":job["job_id"],"project":job["project"],"task":job["task"],"submitted_at":now(),"control_job_sha256":sha(jp)}
 append_event(journal,job["job_id"],"CAPABILITIES_RESOLVED",lifecycle="QUEUED",required_capabilities=job["required_capabilities"])
 w=route(job["required_capabilities"])
 if not w:
  append_event(journal,job["job_id"],"JOB_BLOCKED",lifecycle="BLOCKED",reason="NO_CAPABLE_WORKER")
  receipt.update(status="BLOCKED",reason="NO_CAPABLE_WORKER",required_capabilities=job["required_capabilities"]);(out/"control-receipt.json").write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));return 2
 append_event(journal,job["job_id"],"WORKER_SELECTED",lifecycle="PREPARING",worker_id=w["worker_id"],adapter=w["adapter"])
 op_id=operation_id(job); receipt["operation_id"]=op_id
 reconciliation=reconcile(out/"result.json",op_id)
 append_event(journal,job["job_id"],"RECONCILIATION_CHECKED",lifecycle="PREPARING",operation_id=op_id,action=reconciliation["action"],reason=reconciliation["reason"])
 if reconciliation["action"]=="QUARANTINE":
  append_event(journal,job["job_id"],"JOB_BLOCKED",lifecycle="BLOCKED",reason=reconciliation["reason"])
  receipt.update(status="BLOCKED",reason=reconciliation["reason"]);(out/"control-receipt.json").write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));return 2
 reuse_existing=reconciliation["action"]=="REUSE_RESULT"
 attempt_id="attempt-1"; lease_path=out/"worker-lease.json"
 if not reuse_existing:
  lease=acquire(lease_path,job["job_id"],w["worker_id"],attempt_id,ttl_seconds=job.get("lease_ttl_seconds",300))
  if lease["status"]!="ACQUIRED":
   append_event(journal,job["job_id"],"JOB_BLOCKED",lifecycle="BLOCKED",reason="ACTIVE_LEASE")
   receipt.update(status="BLOCKED",reason="ACTIVE_LEASE");(out/"control-receipt.json").write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));return 2
  append_event(journal,job["job_id"],"LEASE_ACQUIRED",lifecycle="PREPARING",attempt_id=attempt_id,worker_id=w["worker_id"],expires_at=lease["lease"]["expires_at"])
  append_event(journal,job["job_id"],"EXECUTION_STARTED",lifecycle="RUNNING",attempt_id=attempt_id,operation_id=op_id)
 receipt["worker"]={"worker_id":w["worker_id"],"adapter":w["adapter"],"capabilities":w["capabilities"]};ex=job["execution"]
 if reuse_existing:
  result=json.loads((out/"result.json").read_text(encoding="utf-8-sig"))
  receipt.update(status=result.get("status","FAIL"),runtime_result_schema=result.get("schema"),runtime_exit_code=result.get("exit_code"),reconciled=True)
  append_event(journal,job["job_id"],"EXECUTION_RECONCILED",lifecycle="VALIDATING",operation_id=op_id,result_status=result.get("status"))
 elif ex["kind"]=="godot_runtime":
  rj=out/"runtime-job.json";rj.write_text(json.dumps({"schema":"GodotRuntimeJob.v1","job_id":job["job_id"],"project":job["project"],"project_path":ex["project_path"],"mode":ex.get("mode","replay"),"args":ex.get("args",[]),"timeout_seconds":ex.get("timeout_seconds",120),"expected_exit_code":job["validation"]["expected_exit_code"],"operation_id":op_id},indent=2))
  p=subprocess.run([sys.executable,str(FRAMEWORK/"orchestrator/godot-runtime-worker/run_job.py"),str(rj)],capture_output=True,text=True); result=json.loads((out/"result.json").read_text())
  receipt.update(status=result.get("status","FAIL"),runtime_job_sha256=sha(rj),runtime_result_schema=result.get("schema"),runtime_exit_code=result.get("exit_code"),worker_process_exit_code=p.returncode)
 elif ex["kind"]=="executable_runtime":
  exe=Path(ex["executable"]); cmd=[str(exe)]+ex.get("args",[]); p=subprocess.run(cmd,cwd=ex.get("cwd",str(exe.parent)),capture_output=True,text=True,timeout=ex.get("timeout_seconds",120))
  (out/"stdout.log").write_text(p.stdout,encoding="utf-8");(out/"stderr.log").write_text(p.stderr,encoding="utf-8")
  expected=job["validation"]["expected_exit_code"]; status="PASS" if p.returncode==expected else "FAIL"
  result={"schema":"ExecutableRuntimeResult.v1","status":status,"exit_code":p.returncode,"expected_exit_code":expected,"executable":str(exe),"executable_sha256":sha(exe),"stdout_sha256":sha(out/"stdout.log"),"stderr_sha256":sha(out/"stderr.log")}
  (out/"result.json").write_text(json.dumps(result,indent=2));receipt.update(status=status,runtime_result_schema=result["schema"],runtime_exit_code=p.returncode,executable_sha256=result["executable_sha256"])
 elif ex["kind"]=="fidelity_runtime":
  fidelity_job={"schema":"FidelityRuntimeJob.v1","job_id":job["job_id"],"project":job["project"],
     "runtime_kind":ex["runtime_kind"],"capture_mode":ex.get("capture_mode","strict_fidelity"),
     "input_plan":ex.get("input_plan",[]),
     "seed_saves":ex.get("seed_saves"),
     "executable":ex["executable"],"args":ex.get("args",[]),
     "config_source":ex.get("config_source"),"timeout_seconds":ex.get("timeout_seconds",120),
     "window_title_contains":ex.get("window_title_contains"),
     "require_audio":ex.get("require_audio",False),
     "audio_duration_ms":ex.get("audio_duration_ms",3000),
     "capture_delay_seconds":ex.get("capture_delay_seconds",0),
     "capture_schedule_seconds":ex.get("capture_schedule_seconds"),
     "capture_schedule_contract":ex.get("capture_schedule_contract","v1"),
     "capture_backend":ex.get("capture_backend","windows_graphics_capture"),
     "allow_owned_menu_quit":ex.get("allow_owned_menu_quit",False),
     "expected_exit_code":job["validation"]["expected_exit_code"]}
  result=run_fidelity_runtime(fidelity_job,out)
  receipt.update(status=result["status"],runtime_result_schema=result["schema"],
                 runtime_exit_code=result.get("exit_code"),
                 fidelity_block_reason=result.get("failure_reason"),
                 fidelity_isolation_schema=result["isolation_schema"])
 else:raise ValueError("unsupported execution kind")
 append_event(journal,job["job_id"],"EXECUTION_FINISHED",lifecycle="VALIDATING",attempt_id=attempt_id,worker_status=receipt["status"],runtime_exit_code=receipt.get("runtime_exit_code"))
 if not reuse_existing:
  released=release(lease_path,attempt_id)
  append_event(journal,job["job_id"],"LEASE_RELEASED",lifecycle="VALIDATING",attempt_id=attempt_id,released=released)
 append_event(journal,job["job_id"],"VALIDATION_STARTED",lifecycle="VALIDATING")
 validation=validate(job,out/"result.json")
 (out/"validation-result.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
 append_event(journal,job["job_id"],"VALIDATION_FINISHED",lifecycle="VALIDATING",validation_status=validation["status"],worker_result_sha256=validation.get("worker_result_sha256"))
 receipt["worker_status"]=receipt["status"]; receipt["validation_status"]=validation["status"]
 append_event(journal,job["job_id"],"ACCEPTANCE_STARTED",lifecycle="COMMITTING")
 acceptance=accept(job,validation)
 (out/"acceptance-result.json").write_text(json.dumps(acceptance,indent=2),encoding="utf-8")
 append_event(journal,job["job_id"],"ACCEPTANCE_FINISHED",lifecycle="COMMITTING",acceptance_status=acceptance["status"])
 receipt["acceptance_status"]=acceptance["status"]
 blocked_runtime=ex["kind"]=="fidelity_runtime" and result.get("status")=="BLOCKED"
 receipt["status"]="BLOCKED" if blocked_runtime else acceptance["status"]
 final_event="JOB_BLOCKED" if blocked_runtime else ("JOB_COMPLETED" if acceptance["status"]=="PASS" else "JOB_FAILED")
 final_lifecycle="BLOCKED" if blocked_runtime else ("COMPLETED" if acceptance["status"]=="PASS" else "FAILED")
 append_event(journal,job["job_id"],final_event,lifecycle=final_lifecycle)
 receipt["finished_at"]=now();(out/"control-receipt.json").write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2));return 2 if blocked_runtime else (0 if acceptance["status"]=="PASS" else 1)
if __name__=="__main__":
 try:sys.exit(main())
 except Exception as e:print(f"ERROR: {type(e).__name__}: {e}",file=sys.stderr);sys.exit(2)
