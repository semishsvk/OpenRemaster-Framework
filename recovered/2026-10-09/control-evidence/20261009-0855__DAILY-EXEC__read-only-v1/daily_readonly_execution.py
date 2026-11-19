"""2026-10-09 independently bounded read-only OpenRemaster portfolio audit.
Reads canonical corpora and prior evidence; writes only to its unique output folder.
Synthetic scheduler test is NOT ORCH-K003 admission or native execution.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib, json, os, sys, time

HERE = Path(__file__).resolve().parent
HOME = Path(r"F:\Remaster Framework")
CONTROL = HOME / "orchestrator" / "control-plane"
OUT = HOME / "output" / "projects"
PRIOR = OUT / "OpenRemasterOrchestrator" / "reports" / "20261008-135610__AUTONOMOUS-4H-R2__lanes-ABC"
R2_LANE = "20261008-135657__AUTONOMOUS-4H-R2__cycle01"
START = datetime.now(timezone.utc)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def seal(p,obj):
    raw=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    with p.open("xb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
    return sha(p)

corpora = {
  "OpenMDK1": (HOME/"source"/"MDK"/"MDK95.EXE", "profile-a-source-pixel-verification.json"),
  "OpenStonekeep": (HOME/"source"/"Stonekeep"/"SK.EXE", "actor-refresh-verification.json"),
  "OpenUltima8": (HOME/"source"/"Ultima 8"/"ENGLISH"/"U8.EXE", "projected-grid-verification-v2.json"),
}
pins = {}
lanes = {}
for project, (exe, report_name) in corpora.items():
    report_path = OUT/project/"evidence"/R2_LANE/report_name
    report = load(report_path)
    exe_hash = sha(exe)
    cases = report.get("cases",[])
    source_match = exe_hash == report["source_exe_sha256"]
    all_cases_pass = all(c.get("pass") is True for c in cases)
    count_match = len(cases) == report.get("tests")
    dimensions = {
       "OpenMDK1":["flags","material_name","n","profile","ordinal","provider","x_mod32"],
       "OpenStonekeep":["turn_mode","frame","worldphase","active_actors","event","event_blocked","boundary"],
       "OpenUltima8":["grid_fixture","result","shape","source_representative"],
    }[project]
    coverage={k:len({json.dumps(c.get(k),sort_keys=True) for c in cases}) for k in dimensions}
    pins[project]={"source_exe_path":str(exe),"source_exe_sha256":exe_hash,
                   "evidence_path":str(report_path),"evidence_sha256":sha(report_path)}
    lanes[project]={"source_hash_matches_report":source_match,"case_count_matches":count_match,
      "all_cases_pass":all_cases_pass,"tested_cases":len(cases),
      "coverage_unique_values":coverage,
      "original_runtime_executed":report.get("game_runtime_executed",None),
      "full_fidelity_verified":report.get("fidelity_verified",report.get("full_frame_verified",False)),
      "scope_boundary":report.get("next",report.get("negative_barriers",report.get("unknown_grid_authority","not_declared"))),
      "status":"STRUCTURAL_MECHANISM_VALIDATED" if source_match and count_match and all_cases_pass else "FAIL_EVIDENCE"}
    if not (source_match and count_match and all_cases_pass):
        raise RuntimeError("LANE_EVIDENCE_INTEGRITY_FAILED:"+project)

final_audit = load(PRIOR/"final-audit.json")
terminal = load(PRIOR/"TERMINAL_CHECKPOINT.json")
live_state = load(PRIOR/"run-state.json")
terminal_hash_ok = terminal.get("final_audit_sha256")==sha(PRIOR/"final-audit.json")
r2 = {"audit_status":final_audit.get("status"),"audit_problems":final_audit.get("problems"),
      "sealed_status":terminal.get("status"),"terminal_hash_match":terminal_hash_ok,
      "canonical_state_status":live_state.get("status"),
      "state_mismatch":live_state.get("status")!=terminal.get("status"),
      "reconciliation_policy":"Do not rewrite R2 run-state or claim it closed until canonical state transition is authorized and atomic."}
if final_audit.get("status")!="PASS_INTEGRITY" or not terminal_hash_ok:
    raise RuntimeError("R2_TERMINAL_PROVENANCE_FAILURE")

policy_path = CONTROL/"dynamic-lane-scheduler.v1.json"
policy=load(policy_path)
commissioning=load(CONTROL/"worker-commissioning.json")
worker_hb=load(HOME/"orchestrator"/"native-worker"/"queue"/"worker-heartbeat.json")
queue=HOME/"orchestrator"/"native-worker"/"queue"
queue_counts={k:len(list((queue/k).glob("*"))) for k in ("pending","running")}
scheduler_authorized = policy.get("activation") not in ("POLICY_ONLY_UNTIL_NATIVE_SCHEDULER_ADAPTER_TESTED_AND_ADMITTED",None)
# A local worker heartbeat or registry entry cannot grant global dispatch authorization.
admission={"native_worker_heartbeat":worker_hb,"queue_counts":queue_counts,
           "registered_native_status":commissioning["workers"]["HomePC-NativeWorker"]["status"],
           "scheduler_activation":policy.get("activation"),
           "scheduler_dispatch_admitted":bool(scheduler_authorized),
           "production_native_execution_allowed_in_this_run":False,
           "reason":"POLICY_ONLY_SCHEDULER; R2_STATE_MISMATCH; UNRECONCILED_FOREIGN_GODOT_PROCESSES_AND_LEASES"}

modules=["dynamic_scheduler_core_v1.py","dynamic_scheduler_lifecycle_v1.py","dynamic_scheduler_simulator_v1.py"]
module_hashes_before={m:sha(CONTROL/m) for m in modules}
sys.path.insert(0,str(CONTROL))
from dynamic_scheduler_core_v1 import Task,Worker,plan
from dynamic_scheduler_simulator_v1 import simulate
def test_task(p,priority):
    return Task(p,p+"-synthetic",priority,("cpu",),True,True,True,True,True,True,True)
# Five explicitly synthetic scopes test 3 slots, blocked top lane and warm-lane failover.
projects=["OpenMDK1","OpenStonekeep","OpenUltima8","OpenNormality","OpenDescent"]
tasks=[test_task(p,100-i) for i,p in enumerate(projects)]
workers=[Worker("synthetic_cpu_"+str(i),("cpu",),True,True) for i in range(3)]
outcomes={t.task_id:("BLOCKED" if t.project=="OpenMDK1" else "PASS") for t in tasks}
simulation=simulate(tasks,workers,outcomes)
assert simulation["status"]=="SIMULATION_COMPLETE"
assert len(simulation["events"])==5
assert [x["tick"] for x in simulation["events"]]==[0,0,0,1,1]
assert simulation["events"][0]["result"]=="BLOCKED"
assert {x["project"] for x in simulation["events"][3:]}=={"OpenNormality","OpenDescent"}
assert simulation["native_execution"] is False and simulation["leases_modified"] is False
negative_running = plan(tasks,workers,running=[{}])
assert negative_running["status"]=="BLOCKED"
excluded=plan([test_task("OpenAzrael-Retail",300)]+tasks,workers)
assert ("OpenAzrael-Retail-synthetic","PAUSED_OR_CLOSED") in excluded["rejections"]
module_hashes_after={m:sha(CONTROL/m) for m in modules}
assert module_hashes_before==module_hashes_after

checkpoint={
  "schema":"OpenRemaster.DailyReadOnlyExecutionAudit.v1",
  "run_id":"20261009-0855__DAILY-EXEC__read-only-v1",
  "started_utc":START.isoformat(),"finished_utc":datetime.now(timezone.utc).isoformat(),
  "scope":"Read-only source/evidence pin audit and isolated synthetic failover contract test. NO native game execution.",
  "source_pins":pins,"lane_evidence":lanes,"prior_run_reconciliation":r2,
  "current_scheduler_admission":admission,
  "synthetic_scheduler_test":{"status":"PASS_SYNTHETIC_ONLY","events":simulation["events"],
      "negative_incomplete_capacity":negative_running,"paused_retail_rejected":True,
      "source_module_sha256":module_hashes_after},
  "execution_accounting":{"native_heavy_jobs_launched":0,"live_leases_acquired":0,
      "read_only_lanes_completed":3,"fallback_executed":True},
  "result":"PASS_READ_ONLY_AUDIT; NATIVE_DISPATCH_BLOCKED",
  "next_actions":["Canonical R2 CAS/ACL reconciliation (without bypassing file protections)",
      "Real worker-owned native adapter + accurate live process/lease census before native admission",
      "MDK1 original triangle/camera/depth verification","Stonekeep orientation/helper boundary",
      "Ultima8 original runtime grid producer plus placement binding"]
}
hash_out=seal(HERE/"DAILY_CHECKPOINT.json",checkpoint)
seal(HERE/"EVIDENCE_MANIFEST.json",{"schema":"OpenRemaster.DailyEvidenceManifest.v1",
       "checkpoint_sha256":hash_out,"script_sha256":sha(Path(__file__)),
       "input_sha256":{str(p):sha(p) for p in [policy_path,PRIOR/"final-audit.json",PRIOR/"TERMINAL_CHECKPOINT.json",PRIOR/"run-state.json"]}})
print(json.dumps({"result":checkpoint["result"],"checkpoint_sha256":hash_out,
   "lanes":{k:v["tested_cases"] for k,v in lanes.items()},
   "scheduler_fallback_events":simulation["events"],
   "r2_state_mismatch":r2["state_mismatch"],
   "native_dispatch_admitted":admission["scheduler_dispatch_admitted"],
   "elapsed_seconds":(datetime.now(timezone.utc)-START).total_seconds()},indent=2))
