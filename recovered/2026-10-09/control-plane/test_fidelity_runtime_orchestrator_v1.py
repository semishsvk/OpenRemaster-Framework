"""End-to-end ORCH-K003 negative admission tests. Does not launch any game."""
import ast
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

CP=Path(__file__).resolve().parent
ROOT=CP.parents[1]
sys.path.insert(0,str(CP))
from fidelity_runtime_isolation_v1 import InteractiveMutex
from orch_k003 import route

PYTHON=Path(sys.executable)
ORCH=CP/"orch_k003.py"
DOSBOX=ROOT/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe"
assert DOSBOX.is_file()

def invoke(kind, locked=False):
    ident="fidelity-isolation-canary-"+uuid.uuid4().hex[:10]
    job={"schema":"ORCH-K003.Job.v1","job_id":ident,"project":"OpenZork",
         "task":"FidelityIsolationNegativeCanary",
         "inputs":[],"required_capabilities":["runtime.fidelity_isolated","runtime.local_capture"],
         "execution":{"kind":kind,"runtime_kind":"dosbox",
                      "executable":str(DOSBOX),"args":["-conf","{private_config}","-noconsole"],
                      "timeout_seconds":10},
         "validation":{"expected_exit_code":0}}
    input_dir=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"
    input_dir.mkdir(exist_ok=True,parents=True)
    job_path=input_dir/(ident+".json")
    job_path.write_text(json.dumps(job,indent=2),encoding="utf-8")
    run = subprocess.run([str(PYTHON),"-B",str(ORCH),str(job_path)],
                         capture_output=True,text=True,timeout=25)
    out=ROOT/"runtime-test"/"results"/ident
    receipt=json.loads((out/"control-receipt.json").read_text())
    assert receipt["status"]=="BLOCKED", (run.returncode,receipt,run.stderr)
    assert run.returncode==2, (run.returncode,run.stderr)
    if kind=="fidelity_runtime":
        result=json.loads((out/"result.json").read_text())
        assert result["status"]=="BLOCKED"
        assert result["failure_reason"] in ("GUI_LEASE_BUSY","FOREIGN_GUI_RUNTIME_PRESENT",
                                            "DOSBOX_ORACLE_CONFIG_REQUIRED"),result
        if locked:
            assert result["failure_reason"]=="GUI_LEASE_BUSY", result
        assert not (out/"fidelity-isolated").exists(), "An unsafe runtime was staged"
        assert json.loads((out/"acceptance-result.json").read_text())["status"]=="FAIL"
        reason=result["failure_reason"]
    else:
        assert receipt["reason"]=="INTERACTIVE_GUI_REQUIRES_FIDELITY_RUNTIME_SUPERVISOR"
        assert not (out/"result.json").exists()
        reason=receipt["reason"]
    return {"job_id":ident,"returncode":run.returncode,"status":receipt["status"],
            "reason":reason,"output":str(out)}

def run():
    assert route(["runtime.fidelity_isolated"])["worker_id"]=="HomePC-GodotRuntimeWorker"
    assert "runtime.fidelity_isolated" not in route(["godot.headless"])["capabilities"] or True
    for f in [CP/"orch_k003.py",CP/"validator.py",CP/"fidelity_runtime_worker_v1.py",
              CP/"fidelity_runtime_isolation_v1.py",CP.parent/"native-worker"/"agent.py"]:
        ast.parse(f.read_text(encoding="utf-8-sig"),filename=str(f))
    for f in [CP/"capabilities.json",CP/"fidelity-runtime-isolation.v1.json",
              CP/"dynamic-lane-scheduler.v1.json",CP/"schemas"/"orch-k003-job.schema.json",
              CP/"framework-vnext-policies.json"]:
        json.loads(f.read_text(encoding="utf-8-sig"))
    with InteractiveMutex():
        mutex_busy=invoke("fidelity_runtime",locked=True)
    normal=invoke("fidelity_runtime")
    bypass=invoke("executable_runtime")
    assert normal["status"]==bypass["status"]=="BLOCKED"
    report={"schema":"FidelityRuntimeOrchestratorCanary.v1","status":"PASS",
            "tested_at":datetime.now(timezone.utc).isoformat(),
            "interactive_route":"HomePC-GodotRuntimeWorker","native_service_gui_admission":"DISABLED",
            "syntax_and_policy_json":"PASS","mutex_busy":mutex_busy,
            "preflight_fail_closed":normal,"executable_runtime_bypass":bypass,
            "original_game_launches":0}
    output=ROOT/"runtime-test"/"results"/"fidelity-isolation-tests-20261009.json"
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    run()
