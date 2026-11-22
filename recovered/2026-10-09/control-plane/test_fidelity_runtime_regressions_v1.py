"""Regression suite for fidelity isolation, non-destructive and no game launches."""
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
TESTS=(
    "test_leases.py",
    "test_negative_validation.py",
    "test_framework_vnext_policies.py",
    "test_dynamic_scheduler_core_v1.py",
    "test_dynamic_scheduler_dispatch_guard_v1.py",
    "test_idempotency.py",
    "test_fidelity_runtime_isolation_v1.py",
    "test_fidelity_runtime_orchestrator_v1.py",
    "test_fidelity_template_v2.py",
    "test_fidelity_audio_capability_guard_v1.py",
    "test_diagnostic_crash_gating_v3.py",
    "test_targeted_input_admission_v4.py",
    "test_owned_menu_quit_guard_v4.py",
    "test_capture_sequence_contract_v5.py",
    "test_owned_mouse_admission_v5.py",
    "test_readonly_save_seed_v5.py",
    "test_legacy_executable_gui_guard_v6.py",
    "test_owned_mouse_state_canary_v5.py",
    "test_targeted_input_canary_v4.py",
    "test_legacy_entrypoint_migration_v3.py",
    "test_passive_diagnostic_orch_v3.py",
    "test_fidelity_job_object_cleanup_v1.py",
    "test_fidelity_comparator_v1.py",
    "../capture-worker/test_wgc_synthetic_window_v1.py",
    "../capture-worker/test_process_loopback_v1.py",
)
def main():
    rows=[]
    for f in TESTS:
        proc=subprocess.run([sys.executable,"-B",str(CP/f)],
                            cwd=str(CP),capture_output=True,text=True,timeout=40)
        rows.append({"test":f,"status":"PASS" if proc.returncode==0 else "FAIL",
                     "exit":proc.returncode,
                     "stdout_tail":proc.stdout[-500:],"stderr_tail":proc.stderr[-700:]})
    good=all(row["status"]=="PASS" for row in rows)
    report={"schema":"OpenRemaster.FidelityIsolationRegression.v1",
            "tested_at":datetime.now(timezone.utc).isoformat(),
            "status":"PASS" if good else "FAIL",
            "scope":"ORCH-K003 and negative fidelity safety gates, no positive original-runtime capture",
            "cases":rows,"count":len(rows),"passed":sum(x["status"]=="PASS" for x in rows)}
    dest=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009.json"
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"status":report["status"],"count":report["count"],"passed":report["passed"],
                      "failures":[x for x in rows if x["status"]!="PASS"],"evidence":str(dest)}))
    return 0 if good else 1
if __name__=="__main__":
    sys.exit(main())
