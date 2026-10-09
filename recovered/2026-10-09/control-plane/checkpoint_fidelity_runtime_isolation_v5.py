"""Evidence-backed v5 checkpoint for bounded original-game timeline and owned-input holds.
No runtime execution, no process cleanup, no changes to frozen source/policy.
"""
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
import json
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts,process_session,active_console_session
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence

CP=Path(__file__).resolve().parent
ROOT=CP.parents[1]
OUT=ROOT/"runtime-test"/"results"

def path_for(run,file):
 return OUT/run/file
v4=OUT/"fidelity-runtime-isolation-checkpoint-20261009-v4.json"
assert v4.is_file()
reg=OUT/"fidelity-isolation-regressions-20261009.json"
tests=json.loads(reg.read_text(encoding="utf-8-sig"))
assert tests.get("status")=="PASS" and tests.get("count")==23 and tests.get("passed")==23

timeline_run="openzork-dosboxx-threepoint-c0b9fda589"
master=path_for(timeline_run,"fidelity-isolated/capture/capture-attestation.json")
m=json.loads(master.read_text(encoding="utf-8-sig"))
verified=verify_bounded_wgc_sequence(master.parent,m)
assert verified["verified_frames"]==3
assert [x["requested_at_seconds"] for x in m["frames"]]==[10,26,42]
assert len({x["sha256"] for x in m["frames"]})==3
timeline=path_for(timeline_run,"timeline-report.json")
assert json.loads(timeline.read_text())["status"]=="TECHNICAL_SEQUENCE_PASS_ORIGINAL_GAME_FIDELITY_HOLD"

two_run="openzork-dosboxx-two-enters-40edaf1d1"
two_manifest=path_for(two_run,"fidelity-isolated/capture/capture-attestation.json")
two=json.loads(two_manifest.read_text(encoding="utf-8-sig"))
assert verify_bounded_wgc_sequence(two_manifest.parent,two)["verified_frames"]==3
assert two["frames"][1]["sha256"]==two["frames"][2]["sha256"],"Title changed unexpectedly after second enter"
mouse_synth=path_for("fidelity-mouse-owned-51498efa5","mouse-canary.json")
s=json.loads(mouse_synth.read_text(encoding="utf-8-sig"))
assert s["status"]=="PASS" and s["original_red_blue_to_green_yellow"] is True
assert s["global_mouse_moved"] is False
mouse_game_run="openzork-newgame-owned-mouse-f7680fb8f"
mouse_game=path_for(mouse_game_run,"owned-mouse-state-probe.json")
g=json.loads(mouse_game.read_text(encoding="utf-8-sig"))
assert g["status"]=="INPUT_DELIVERY_AND_CAPTURE_TECHNICAL_PASS_STATE_REVIEW_REQUIRED"
assert g["runtime_exit"]==0 and g["fidelity_verified"] is False
assert g["click_client"]==[215,235]
assert g["image_measurements"]["fraction_pixel_changed_vs_original_title"]<0.01
record=path_for(mouse_game_run,"result.json")
g_result=json.loads(record.read_text())
events=g_result.get("owned_input_posted_events") or []
assert len(events)==1 and events[0]["action"]=="MOUSE_LEFT_CLICK"
assert events[0]["global_SendInput_used"] is False
assert events[0]["global_SetCursorPos_used"] is False
assert events[0]["focus_switched"] is False
bad=path_for("openzork-newgame-owned-mouse-7b5f2dda5","result.json")
b=json.loads(bad.read_text())
assert b["failure_reason"]=="OWNED_MOUSE_CLICK_OUTSIDE_CLIENT"
assert b["failure_details"]["width"]==426 and b["failure_details"]["height"]==320
assert b["failure_details"]["y"]==352

original=CP/"framework-vnext-policies.json"
backup=ROOT/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
assert sha256(original)==sha256(backup)
artifacts=[
 "orchestrator/control-plane/FIDELITY_RUNTIME_ISOLATION_V5.md",
 "orchestrator/control-plane/fidelity-runtime-isolation.v5.json",
 "orchestrator/control-plane/fidelity_capture_sequence_v1.py",
 "orchestrator/control-plane/fidelity_owned_mouse_v1.py",
 "orchestrator/control-plane/fidelity_targeted_input_v1.py",
 "orchestrator/control-plane/fidelity_runtime_worker_v1.py",
 "orchestrator/control-plane/fidelity_local_capture_wgc_v1.py",
 "orchestrator/control-plane/fidelity_local_audio_loopback_v1.py",
 "orchestrator/control-plane/fidelity_runtime_isolation_v1.py",
 "orchestrator/control-plane/orch_k003.py",
 "orchestrator/control-plane/validator.py",
 "orchestrator/control-plane/capabilities.json",
 "orchestrator/control-plane/schemas/orch-k003-job.schema.json",
 "orchestrator/control-plane/test_capture_sequence_contract_v5.py",
 "orchestrator/control-plane/test_owned_mouse_state_canary_v5.py",
 "orchestrator/control-plane/test_owned_mouse_admission_v5.py",
 "orchestrator/control-plane/test_openzork_dosboxx_frame_sequence_v5.py",
 "orchestrator/control-plane/test_openzork_dosboxx_two_enters_v5.py",
 "orchestrator/control-plane/test_openzork_dosboxx_newgame_mouse_v5.py",
 "orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py",
 "orchestrator/control-plane/examples/OpenZork-dosboxx-autotype-two-enters-v5.conf",
 "orchestrator/capture-worker/capture_window_wgc.exe",
 "orchestrator/capture-worker/capture_process_audio.exe",
 "work/OpenRemaster/fidelity_fixture/synthetic_scummvm_oracle.exe"
]
files=[]
for relative in artifacts:
 p=ROOT/relative
 if not p.is_file():raise FileNotFoundError(relative)
 files.append({"path":relative,"sha256":sha256(p),"bytes":p.stat().st_size})
proof={
 "timed_threepoint_game_sequence":timeline,
 "timed_threepoint_analysis":path_for(timeline_run,"timeline-analysis.json"),
 "timed_threepoint_contact_sheet":path_for(timeline_run,"original-runtime-timeline.png"),
 "multi_frame_master_manifest":master,
 "double_enter_control":path_for(two_run,"two-enters-hypothesis-report.json"),
 "mouse_synthetic_positive":mouse_synth,
 "mouse_real_menu_negative":mouse_game,
 "mouse_dpi_guard":bad,
 "regressions":reg,
 "v4_checkpoint":v4
}
for key,p in proof.items():assert p.is_file(),(key,str(p))
windows=gui_conflicts()
side=CP/"fidelity-runtime-isolation.v5.json"
sd=json.loads(side.read_text(encoding="utf-8-sig"))
assert sd["state"]=="SUPERVISED_ORIGINAL_TITLE_TIMELINE_TECHNICAL_PASS_GAMEPLAY_INPUT_HOLD"
report={
 "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v5",
 "created_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"SUPERVISED_ORIGINAL_TITLE_TIMELINE_TECHNICAL_PASS_GAMEPLAY_INPUT_HOLD",
 "runtime_evidence_levels":{
   "ORIGINAL_RUNTIME_OBSERVATION":"PASS_FOR_DOSBOX_X_ORIGINAL_NATIVE_GAME",
   "ALIGNED_GAMEPLAY_REPLAY":"NOT_RUN",
   "FIDELITY_ATTESTED":"HOLD",
   "SYNTHETIC_HWND_MOUSE":"PASS",
   "DOSBOX_X_GUEST_MOUSE_CLICK":"NOT_VERIFIED",
   "DOSBOX_X_MENU_NEW_GAME":"NOT_SELECTED"
 },
 "read_only_source":True,
 "frozen_policy_sha256":sha256(original),
 "parent_v4_checkpoint_sha256":sha256(v4),
 "regressions":{"status":"PASS","passed":tests["passed"],"total":tests["count"],"sha256":sha256(reg)},
 "source_original_title_timeline":{"pid":m["pid"],"hwnd":m["hwnd"],
       "timing_points_seconds":[10,26,42],
       "frames_verified":verified["verified_frames"],
       "manifest_sha256":sha256(master),
       "unique_hashes":len({x["sha256"] for x in m["frames"]}),
       "game_content":["POST_PROMPT_TRANSITION","GOLD_INTRO","ZORK_NEMESIS_TITLE_MENU"],
       "emulator":"DOSBOX_X_2026.10.01_NOT_BUNDLED_DOSBOX_0.74"},
 "mouse_input_qualifications":{
    "wrong_dpi_click":"BLOCKED_BEFORE_POSTING",
    "logical_client_during_failure":[426,320],
    "synthetic_state_changed":True,
    "original_game_menu_input_received":"NOT_VERIFIED",
    "title_pixel_changed_fraction":g["image_measurements"]["fraction_pixel_changed_vs_original_title"],
    "two_enter_control_title_unchanged":True,
    "no_global_cursor_or_focus":True
 },
 "current_homepc":{
   "interactive_session":active_console_session(),
   "worker_session":process_session(__import__("os").getpid()),
   "legacy_game_gui_windows":len(windows),
   "legacy_game_gui_pids":len({x["pid"] for x in windows}),
   "window_type_counts":dict(Counter(Path(x["executable"]).name for x in windows)),
   "owner_state":"UNRECONCILED_LEGACY_DO_NOT_KILL_BY_NAME"
 },
 "control_policy":{
   "global_gui_mutex":"Global\\OpenRemaster_HomePC_InteractiveFidelity_v1",
   "managed_interactive_slots":1,"max_heavy_slots":3,
   "capture_authority":"LOCAL_WGC_PROCESS_LOOPBACK_ONLY",
   "RDC_video_fidelity_authority":False,
   "managed_diagnostic_never_fidelity_pass":True,
   "legacy_direct_launchers_all_migrated":False
 },
 "artifacts":files,
 "evidence":[{"name":key,"path":str(p),"sha256":sha256(p)} for key,p in proof.items()],
 "recover":{
  "checksum_all_artifacts":True,
  "older_v4_checkpoint":str(v4),
  "backup_before_mouse":"orchestrator/backups/fidelity-mouse-v5-prechange-20261009",
  "rerun":"orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py",
  "no_background_job_started":True,
  "no_unowned_gui_cleanup":True
 },
 "next_gate":"EMULATOR_NATIVE_MOUSE_INPUT_ADAPTER_WITH_VERIFIED_STATE_DELTA_THEN_ALIGNED_GAMEPLAY_CAPTURE"
}
dest=OUT/"fidelity-runtime-isolation-checkpoint-20261009-v5.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":report["schema"],
"status":report["status"],"test_pass":tests["passed"],"test_total":tests["count"],
"artifact_count":len(files),"evidence_count":len(report["evidence"]),
"original_title_frames":verified["verified_frames"],
"legacy_gui_pids":report["current_homepc"]["legacy_game_gui_pids"],
"frozen_policy_sha256":report["frozen_policy_sha256"],
"checkpoint":str(dest),"sha256":sha256(dest),
"next_gate":report["next_gate"]},ensure_ascii=False))
