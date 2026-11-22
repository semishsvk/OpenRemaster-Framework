"""V4 durable auditable integration checkpoint. No game process launch or cleanup.
Records evidence and distinct levels without asserting fidelity success.
"""
import hashlib,json,platform,os
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from fidelity_runtime_isolation_v1 import gui_conflicts,process_session,active_console_session,sha256

cp=Path(__file__).resolve().parent
root=cp.parents[1]
out=root/"runtime-test"/"results"
checks={
 "regression":out/"fidelity-isolation-regressions-20261009.json",
 "ZORKDOS_prompt":out/"openzork-native-dosbox-passive-ca496ab07"/"native-dosbox-passive-diagnostic.json",
 "ZORKDOS_win32_post_key_negative":out/"openzork-dosbox-hwnd-input-5bf3aa64f"/"input-state-diagnostic.json",
 "DOSBoxX_autotype_transition":out/"openzork-dosboxx-autotype-3956dd7a57"/"dosboxx-autotype-evidence.json",
 "DOSBoxX_no_autotype_control":out/"openzork-dosboxx-control-no-autotype-a732855c"/"matched-control-report.json",
 "DOSBoxX_intro_gold_logo":out/"openzork-dosboxx-late-autotype-e5946df0ec"/"late-capture-report.json",
 "ScummVM_intro_video_audio":out/"openzork-supervised-oracle-passive-93f5cb58c"/"supervised-diagnostic-summary.json",
 "HWND_synthetic_state_delta":out/"fidelity-hwnd-targeted-input-97a07d6bb4"/"targeted-input-canary.json",
 "legacy_wrapper_proof":out/"openzork-legacy-entrypoint-canary-v3.json",
 "ScummVM_record_smoke_crash_revoked":out/"openzork-legacy-record-smoke-77df5799e1"/"technical-pass-invalidation-v3.json",
 "ownership_preflight":out/"fidelity-gui-current-owner-audit-v3.json"
}
missing=[key for key,p in checks.items() if not p.is_file()]
assert not missing,missing
reg=json.loads(checks["regression"].read_text(encoding="utf-8"))
assert reg["status"]=="PASS" and reg["passed"]==20 and reg["count"]==20
gold=json.loads(checks["DOSBoxX_intro_gold_logo"].read_text(encoding="utf-8"))
assert gold["status"]=="TECHNICAL_CAPTURE_PASS_STATE_UNALIGNED" and gold["process_exit"]==0 and gold["fidelity_verified"] is False
autotype=json.loads(checks["DOSBoxX_autotype_transition"].read_text(encoding="utf-8"))
assert autotype["native_runtime_exit_code"]==0 and autotype["fidelity_verified"] is False
contrast=json.loads(checks["DOSBoxX_no_autotype_control"].read_text(encoding="utf-8"))
assert contrast["same_emulator_sha256"] is True and contrast["original_fidelity"]=="NOT_VERIFIED"
sc=json.loads(checks["ScummVM_intro_video_audio"].read_text(encoding="utf-8"))
assert sc["status"]=="PASS" and sc["original_runtime_fidelity"]=="NOT_VERIFIED" and bool(sc.get("audio_sha256"))
negative=json.loads(checks["ZORKDOS_win32_post_key_negative"].read_text(encoding="utf-8"))
assert negative["status"]=="INPUT_STATE_UNVERIFIED" and negative["fidelity_verified"] is False
assert json.loads(checks["ScummVM_record_smoke_crash_revoked"].read_text(encoding="utf-8"))["status"]=="TECHNICAL_DIAGNOSTIC_PASS_REVOKED_ABNORMAL_RUNTIME_EXIT"
original_policy=cp/"framework-vnext-policies.json"
backup_policy=root/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
assert sha256(original_policy)==sha256(backup_policy), "FROZEN POLICY CHANGED"
v2=out/"fidelity-runtime-isolation-checkpoint-20261009-v2.json"
assert v2.is_file()
cpfiles=[
 "orchestrator/control-plane/FIDELITY_RUNTIME_ISOLATION_V4.md",
 "orchestrator/control-plane/fidelity_runtime_isolation_v1.py",
 "orchestrator/control-plane/fidelity_runtime_worker_v1.py",
 "orchestrator/control-plane/fidelity_local_capture_wgc_v1.py",
 "orchestrator/control-plane/fidelity_local_audio_loopback_v1.py",
 "orchestrator/control-plane/fidelity_targeted_input_v1.py",
 "orchestrator/control-plane/fidelity_owned_window_menu_v1.py",
 "orchestrator/control-plane/fidelity_legacy_launcher_bridge_v3.py",
 "orchestrator/control-plane/fidelity-runtime-isolation.v1.json",
 "orchestrator/control-plane/fidelity-runtime-isolation.v3.json",
 "orchestrator/control-plane/orch_k003.py",
 "orchestrator/control-plane/validator.py",
 "orchestrator/control-plane/capabilities.json",
 "orchestrator/control-plane/schemas/orch-k003-job.schema.json",
 "orchestrator/control-plane/dynamic-lane-scheduler.v1.json",
 "orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py",
 "orchestrator/control-plane/test_targeted_input_canary_v4.py",
 "orchestrator/control-plane/test_owned_menu_quit_guard_v4.py",
 "orchestrator/control-plane/test_targeted_input_admission_v4.py",
 "orchestrator/capture-worker/capture_window_wgc.cpp",
 "orchestrator/capture-worker/capture_window_wgc.exe",
 "orchestrator/capture-worker/capture_process_audio.cpp",
 "orchestrator/capture-worker/capture_process_audio.exe",
 "work/OpenRemaster/fidelity_fixture/synthetic_scummvm_oracle.cpp",
 "work/OpenRemaster/fidelity_fixture/synthetic_scummvm_oracle.exe",
 "orchestrator/control-plane/examples/OpenZork-dosboxx-autotype-oracle-seed.conf",
 "orchestrator/control-plane/examples/OpenZork-dosboxx-no-autotype-control-seed.conf",
 "orchestrator/control-plane/examples/OpenZork-dosbox-fidelity-seed.conf",
 "orchestrator/control-plane/examples/OpenZork-scummvm-fidelity-template.json",
 "orchestrator/control-plane/examples/OpenZork-dosbox-fidelity-template.json",
 "work/OpenZork/oracle-runtime/launch-smoke.ps1",
 "work/OpenZork/oracle-runtime/record-smoke.ps1"
]
artifacts=[]
for relative in cpfiles:
 f=root/relative
 if not f.is_file(): raise FileNotFoundError(relative)
 artifacts.append({"path":relative,"sha256":sha256(f),"bytes":f.stat().st_size})
windows=gui_conflicts()
counts=Counter(Path(w["executable"]).name for w in windows)
evidence=[{"purpose":key,"path":str(f),"sha256":sha256(f)} for key,f in checks.items()]
report={
 "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v4",
 "created_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"ORIGINAL_RUNTIME_CONTROL_AND_CAPTURE_TECHNICAL_PASS_GAMEPLAY_FIDELITY_HOLD",
 "phase1_frozen_baseline":"UNCHANGED",
 "original_policy_sha256":sha256(original_policy),
 "prev_checkpoint_sha256":sha256(v2),
 "source_corpus_immutability":"NO_CORPUS_WRITES_IN_THIS_IMPLEMENTATION",
 "integrated_original_runtime_oracles":{
   "bundled_dosbox_074":{"original_ZORKDOS_exe":"VERIFIED_RUNNING","progress":"PROMPT_OBSERVED","win32_hwnd_key_consumed":"NO_PROOF"},
   "dosboxx_2026_10_01":{"original_ZORKDOS_exe":"VERIFIED_RUNNING","internal_autotype":"SUPPORTED_BY_CONTROL_COMPARISON","late_observation":"ORIGINAL_GOLD_INTRO","process_exit":"CLEAN_0","fidelity":"NOT_VERIFIED"},
   "scummvm_200":{"original_Zork_Nemesis_data":"READ_ONLY","intro_audio_video":"CAPTURED_TECHNICAL_PASS","emulator_identity":"SCUMMVM_NOT_ORIGINAL_DOS_EXECUTION","fidelity":"NOT_VERIFIED"}
 },
 "execution_contract":{
   "interactive_gui_slots":1,
   "max_heavy_slots":3,
   "native_service_session0_gui":"UNROUTABLE",
   "strict_mode":"FOREIGN_GUI_FAIL_CLOSED",
   "passive_diagnostic":"EXPLICIT_OPT_IN_NO_FIDELITY_PROMOTION",
   "targeted_input":"ONLY_ALLOWED_KEY_TO_OWNED_PID_HWND_NO_SENDINPUT",
   "emulator_native_autotype":"DOSBOXX_PRIOR_ART_GAME_SPECIFIC_VALIDATION_REQUIRED",
   "managed_gui_lease":"Global\\OpenRemaster_HomePC_InteractiveFidelity_v1",
   "cleanup":"OWNED_JOB_OBJECT_ONLY"
 },
 "regression":{"status":"PASS","passed":20,"total":20,"result_sha256":sha256(checks["regression"])},
 "homepc_snapshot":{"interactive_session":active_console_session(),"current_process_session":process_session(os.getpid()),
                    "unmanaged_visible_game_windows":len(windows),
                    "unmanaged_visible_game_pids":len(set(w["pid"] for w in windows)),
                    "windows_by_executable":dict(counts)},
 "evidence":evidence,
 "artifacts":artifacts,
 "not_verified":["same-state-original-vs-Godot gameplay replay",
                 "pixel-aligned and audio-aligned fidelity comparison",
                 "gameplay navigation and interaction control",
                 "cleanup of unowned legacy process list",
                 "all external/direct legacy GUI entrypoints migrated"],
 "recovery":{
   "readme":"orchestrator/control-plane/FIDELITY_RUNTIME_ISOLATION_V4.md",
   "pre_v3_backups":"orchestrator/backups/fidelity-isolation-before-v3-20261009",
   "legacy_entrypoint_backup":"orchestrator/backups/openzork-legacy-gui-launchers-20261009-v3",
   "build_native_capture":"orchestrator/capture-worker/build_capture_worker.py and build_audio_worker.py",
   "verify":"orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py",
   "restore_precondition":"verify all artifact hashes and process owners; no restart or global kill"
 }
}
dest=out/"fidelity-runtime-isolation-checkpoint-20261009-v4.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":report["schema"],"status":report["status"],
                   "regressions_passed":20,"source_frozen_hash":report["original_policy_sha256"],
                   "count_artifacts":len(artifacts),"count_evidence":len(evidence),
                   "GUI_windows_now":len(windows),"GUI_pids_now":len(set(w["pid"] for w in windows)),
                   "path":str(dest),"checkpoint_sha256":sha256(dest)},ensure_ascii=False))
