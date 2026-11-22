"""Capture a durability/status checkpoint; archive failed one-time migration script.
Does not alter any game corpus, kill processes, or promote fidelity.
"""
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys
from fidelity_runtime_isolation_v1 import gui_conflicts, sha256, active_console_session, process_session

CP=Path(__file__).resolve().parent
ROOT=CP.parents[1]
BACKUP=ROOT/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"
BACKUP.mkdir(exist_ok=True,parents=True)
protected=CP/"framework-vnext-policies.json"
protected_original=BACKUP/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
assert protected_original.is_file()
assert sha256(protected)==sha256(protected_original), "Baseline policy was modified; stop reporting success"
proposed=CP/"framework-vnext-policies.json.fidelity-integration.tmp"
if proposed.is_file():
    dest=BACKUP/"policy-proposal-not-applied.json"
    if dest.exists():
        assert sha256(dest)==sha256(proposed)
        proposed.unlink()
    else:
        shutil.move(str(proposed),str(dest))
migration=CP/"apply_fidelity_isolation_v1.py"
if migration.is_file():
    dest=BACKUP/"initial-partial-migration-script.py"
    if not dest.exists():
        shutil.move(str(migration),str(dest))
paths=[
    CP/"fidelity_runtime_isolation_v1.py",
    CP/"fidelity_runtime_worker_v1.py",
    CP/"orch_k003.py",
    CP/"validator.py",
    CP/"capabilities.json",
    CP/"schemas"/"orch-k003-job.schema.json",
    CP/"dynamic-lane-scheduler.v1.json",
    CP/"fidelity-runtime-isolation.v1.json",
    CP/"FIDELITY_RUNTIME_ISOLATION_V1.md",
    CP/"examples"/"OpenZork-dosbox-fidelity-template.json",
    CP.parent/"native-worker"/"agent.py",
    CP/"test_fidelity_runtime_isolation_v1.py",
    CP/"test_fidelity_runtime_orchestrator_v1.py",
    CP/"test_fidelity_comparator_v1.py",
    CP/"test_fidelity_runtime_regressions_v1.py"
]
assert all(p.is_file() for p in paths)
regression=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009.json"
assert json.loads(regression.read_text())["status"]=="PASS"
windows=gui_conflicts()
groups=Counter(Path(w["executable"]).name for w in windows)
report={
    "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v1",
    "status":"INTEGRATED_NEGATIVE_CANARY_PASS_CAPTURE_PRODUCER_HOLD",
    "date_utc":datetime.now(timezone.utc).isoformat(),
    "homepc":{"os":platform.platform(),
              "interactive_session":active_console_session(),
              "worker_session":process_session(__import__("os").getpid()),
              "conflicting_gui_windows":len(windows),
              "conflicting_gui_pids":len({w["pid"] for w in windows}),
              "windows_by_executable":dict(groups),
              "preflight_policy":"BLOCK_FOREIGN_GUI",
              "legacy_gui_cleanup":"NOT_PERFORMED"},
    "admission":{"global_mutex":"Global\\OpenRemaster_HomePC_InteractiveFidelity_v1",
                 "interactive_gui_slots":1,"headless_heavy_slots_unchanged":3,
                 "gui_worker":"HomePC-GodotRuntimeWorker","native_session_0_gui":"NOT_ROUTABLE",
                 "direct_managed_executable_gui":"BLOCKED",
                 "runtime_pid_hwnd_sha":"REQUIRED"},
    "capture":{"WGC_producer":"NOT_IMPLEMENTED","process_loopback_producer":"NOT_IMPLEMENTED",
               "local_capture_attestation_validation":"NEGATIVE_PASS",
               "independent_byte_exact_comparison":"SYNTHETIC_PASS",
               "actual_game_fidelity":"NOT_VERIFIED"},
    "tests":{"regression_suite_count":8,"regression_pass":8,
             "synthetic_comparator":"PASS",
             "original_runtime_live_capture":"NOT_RUN_EXISTING_GUI_CONFLICTS"},
    "phase1":{"frozen_baseline":"UNCHANGED",
              "original_framework_policy_sha256":sha256(protected),
              "original_corpus_writes":"NONE_BY_THIS_IMPLEMENTATION"},
    "files":[{"path":str(p.relative_to(ROOT)),"sha256":sha256(p),"bytes":p.stat().st_size} for p in paths],
    "previous_file_backups":str(BACKUP),
    "migration_note":"Policy original atomic replacement denied; sidecar added, original remains identical to backup",
    "residual_risk":"Legacy direct DOSBox/ScummVM/Godot launchers not automatically intercepted; migrate project adapters",
}
dest=ROOT/"runtime-test"/"results"/"fidelity-runtime-isolation-checkpoint-20261009-v1.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":report["schema"],"status":report["status"],
                  "gui_conflicting_windows":len(windows),
                  "gui_conflicting_pids":report["homepc"]["conflicting_gui_pids"],
                  "regression_pass":report["tests"]["regression_pass"],
                  "frozen_policy_sha256":report["phase1"]["original_framework_policy_sha256"],
                  "artifact_count":len(paths),"checkpoint":str(dest),
                  "next_gate":"RECONCILE_PREEXISTING_RUNTIMES_AND_COMMISSION_HWND_CAPTURE"},
                  ensure_ascii=False))
