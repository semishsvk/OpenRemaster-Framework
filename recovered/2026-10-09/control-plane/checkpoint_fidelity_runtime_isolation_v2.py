"""Evidence checkpoint for scoped GUI+audio fidelity capture isolation.
Read-only inventory plus one checkpoint write. Does not launch or close game processes.
"""
from collections import Counter
from datetime import datetime, timezone
import json, os, platform
from pathlib import Path
from fidelity_runtime_isolation_v1 import sha256, gui_conflicts, active_console_session, process_session

CP=Path(__file__).resolve().parent
ROOT=CP.parents[1]
OUT=ROOT/"runtime-test"/"results"
SIDE=CP/"fidelity-runtime-isolation.v1.json"
POLICY=CP/"framework-vnext-policies.json"
BACKUP=ROOT/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
REGRESSION=OUT/"fidelity-isolation-regressions-20261009.json"
REG=json.loads(REGRESSION.read_text(encoding="utf-8"))
assert REG.get("status")=="PASS" and REG.get("count")==13 and REG.get("passed")==13
assert sha256(POLICY)==sha256(BACKUP),"Frozen policy baseline unexpectedly changed"
side=json.loads(SIDE.read_text(encoding="utf-8-sig"))
assert side["schema"]=="OpenRemaster.FidelityRuntimeIsolation.v1"
assert side["max_interactive_fidelity_jobs"]==1 and side["max_total_heavy_jobs_unchanged"]==3
assert side["original_game_fidelity"]=="NOT_VERIFIED"
binpaths=[]
for k,settings in side["capture_producers"].items():
 p=ROOT/settings["path"]
 assert p.is_file() and sha256(p)==settings["sha256"],f"Capture executable fingerprint changed: {k}"
 binpaths.append(str(p))
required=[
 CP/"fidelity_runtime_isolation_v1.py",
 CP/"fidelity_runtime_worker_v1.py",
 CP/"fidelity_local_capture_wgc_v1.py",
 CP/"fidelity_local_audio_loopback_v1.py",
 CP/"orch_k003.py",
 CP/"validator.py",
 CP/"capabilities.json",
 CP/"dynamic-lane-scheduler.v1.json",
 CP/"schemas"/"orch-k003-job.schema.json",
 CP/"FIDELITY_RUNTIME_ISOLATION_V1.md",
 CP/"examples"/"OpenZork-dosbox-fidelity-template.json",
 CP/"examples"/"OpenZork-scummvm-fidelity-template.json",
 CP/"examples"/"OpenZork-dosbox-fidelity-seed.conf",
 ROOT/"orchestrator"/"capture-worker"/"capture_window_wgc.cpp",
 ROOT/"orchestrator"/"capture-worker"/"capture_process_audio.cpp",
 ROOT/"orchestrator"/"capture-worker"/"capture_window_wgc.exe",
 ROOT/"orchestrator"/"capture-worker"/"capture_process_audio.exe",
 ROOT/"orchestrator"/"native-worker"/"agent.py"
]
assert all(f.is_file() for f in required)
image_dirs=sorted(OUT.glob("wgc-synthetic-*"),key=lambda f:f.stat().st_mtime,reverse=True)
image_json=next((f/"canary-result.json" for f in image_dirs if (f/"canary-result.json").is_file()),None)
assert image_json
wgc=json.loads(image_json.read_text(encoding="utf-8"))
assert wgc["status"]=="PASS" and wgc.get("process_audio_sha256")
audio_dirs=sorted(OUT.glob("process-loopback-*"),key=lambda f:f.stat().st_mtime,reverse=True)
audio_json=next((f/"audio-canary.json" for f in audio_dirs if (f/"audio-canary.json").exists()),None)
assert audio_json
audio=json.loads(audio_json.read_text(encoding="utf-8"))
assert audio["status"]=="PASS" and audio["silent_max_abs_sample"]<=1

visual_diags=sorted(OUT.glob("wgc-existing-windows-diagnostic-*"),key=lambda f:f.stat().st_mtime,reverse=True)
vpath=next((d/"diagnostic-report.json" for d in visual_diags if (d/"diagnostic-report.json").is_file()),None)
assert vpath
v=json.loads(vpath.read_text(encoding="utf-8"))
assert v.get("valid_count")==3 and v.get("distinct_frame_hashes")==3

auddiags=sorted(OUT.glob("process-audio-existing-diagnostic-*"),key=lambda f:f.stat().st_mtime,reverse=True)
apath=next((d/"diagnostic-report.json" for d in auddiags if (d/"diagnostic-report.json").is_file()),None)
assert apath
a=json.loads(apath.read_text(encoding="utf-8"))
assert len(a["rows"])==2 and all(x["status"]=="DIAGNOSTIC_PROCESS_AUDIO" for x in a["rows"])

windows=gui_conflicts()
report={
 "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v2",
 "status":"LOCAL_VIDEO_AUDIO_CAPTURE_TECHNICAL_PASS_ORIGINAL_FIDELITY_HOLD",
 "date_utc":datetime.now(timezone.utc).isoformat(),
 "scope":"HomePC/orchestrator/control-plane; all projects via common fidelity_runtime execution kind",
 "activation":"OPT_IN_ONLY_LEGACY_DIRECT_GUI_LAUNCHERS_NOT_YET_INTERCEPTED",
 "execution":{
   "live_console_session":active_console_session(),
   "running_this_checkpoint_in_session":process_session(os.getpid()),
   "fidelity_gui_slots":1,"heavy_slots":3,
   "routed_gui_worker":"HomePC-GodotRuntimeWorker",
   "native_service_session0_gui":"NOT_ROUTABLE",
   "global_mutex":side["named_mutex"],
   "preflight_conflicting_windows_now":len(windows),
   "preflight_conflicting_pids_now":len({w["pid"] for w in windows}),
   "windows_by_executable":dict(Counter(Path(w["executable"]).name for w in windows)),
   "foreign_gui_no_auto_cleanup":True
 },
 "capture":{
   "local_wgc_exe_sha256":side["capture_producers"]["window_wgc"]["sha256"],
   "local_process_loopback_exe_sha256":side["capture_producers"]["process_loopback"]["sha256"],
   "synthetic_integrated_video_audio":"PASS",
   "synthetic_process_isolation":"PASS",
   "unowned_original_gui_wgc_diagnostic":{"status":"PASS_DIAGNOSTIC_ONLY","n":3,"unique_hashes":3},
   "unowned_original_process_audio_diagnostic":{"status":"PASS_DIAGNOSTIC_ONLY","n":2},
   "remote_desktop_capture_authority":False,
   "original_game_fidelity":"NOT_VERIFIED",
   "independent_byte_exact_comparison":"SYNTHETIC_PASS_ONLY"
 },
 "safety":{
   "canonical_source_writes":"NONE_BY_CURRENT_MIGRATION",
   "frozen_phase1":"UNCHANGED",
   "original_policy_sha256":sha256(POLICY),
   "stop_unowned_processes":"NEVER",
   "fail_closed_when_gui_contaminated":True,
   "source_mount_must_be_read_only":True,
   "all_writable_dosbox_mounts_must_be_run_private":True,
   "audio_binds_to_process_tree":True
 },
 "regression":{"status":"PASS","passed":13,"total":13,"evidence":str(REGRESSION),"sha256":sha256(REGRESSION)},
 "evidence":[
   {"kind":"synthetic-video-and-audio","path":str(image_json),"sha256":sha256(image_json)},
   {"kind":"process-audio-isolation","path":str(audio_json),"sha256":sha256(audio_json)},
   {"kind":"existing-dosbox-scummvm-godot-window-diagnostics","path":str(vpath),"sha256":sha256(vpath)},
   {"kind":"existing-dosbox-scummvm-audio-diagnostics","path":str(apath),"sha256":sha256(apath)}
 ],
 "artifacts":[{"path":str(f.relative_to(ROOT)),"sha256":sha256(f),"bytes":f.stat().st_size} for f in required],
 "original_policy_sidecar":str(SIDE),
 "backups":str(BACKUP.parents[2]),
 "restore_recipe":[
   "Verify every artifacts[].sha256 and the original frozen policy hash.",
   "Rebuild native capture exes with VS2022 vcvars64.bat and capture-worker/build_capture_worker.py + build_audio_worker.py in isolated worker dir.",
   "Run control-plane/test_fidelity_runtime_regressions_v1.py in an interactive HomePC desktop session.",
   "Do not start first original-runtime fidelity job while foreign interactive GUI windows remain.",
   "Do not claim FIDELITY_VERIFIED until an original-runtime vs reconstructed capture has run through independent alignment/comparison and source provenance."
 ],
 "blocking_next_gates":[
   "RECONCILE_AND_SAFELY_RETIRE_LEGACY_GUI_PROCESSES_WITH_OWNER_EVIDENCE",
   "MIGRATE_DIRECT_DOSBOX_SCUMMVM_GODOT_GUI_LAUNCHERS",
   "SUPERVISED_ORIGINAL_RUNTIME_REPLAY_WITH_LOCAL_CAPTURE",
   "INDEPENDENT_ORIGINAL_VS_RECONSTRUCTION_FIDELITY_COMPARISON"
 ]
}
dest=OUT/"fidelity-runtime-isolation-checkpoint-20261009-v2.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({
 "schema":report["schema"],"status":report["status"],
 "test_pass":report["regression"]["passed"],"video_synthetic":"PASS","audio_synthetic":"PASS",
 "diagnostic_real_windows":3,"diagnostic_real_audio":2,
 "foreign_gui_windows":len(windows),"foreign_gui_pids":len({w["pid"] for w in windows}),
 "artifact_count":len(required),"baseline_policy_hash":sha256(POLICY),
 "checkpoint":str(dest),"sha256":sha256(dest)},ensure_ascii=False))
