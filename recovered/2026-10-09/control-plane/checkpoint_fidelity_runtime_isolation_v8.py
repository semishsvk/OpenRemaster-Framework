"""Durable evidence-backed incremental v8 checkpoint; no GUI launches or kills.
Seals native original ZORKDOS New Game/Space/courtyard one-run positive and
three failure-mode controls without promoting Godot fidelity or repeatability.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,platform
from collections import Counter
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts,active_console_session,process_session
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
RES=R/"runtime-test"/"results"
R9=RES/"openzork-native-dosboxx-cursor-feedback-newgame-20261009-r9"
R10=RES/"openzork-native-dosboxx-cursor-feedback-newgame-20261009-r10"

def read(p):
 p=Path(p)
 if not p.is_file():raise FileNotFoundError(str(p))
 return json.loads(p.read_text(encoding="utf-8-sig"))

prior=RES/"fidelity-runtime-isolation-checkpoint-20261009-v7.json"
old=read(prior)
assert old["schema"]=="OpenRemaster.FidelityRuntimeIsolationCheckpoint.v7"
assert sha256(prior)=="829ac826c8ac500567b48d0b081b1b9157a6c4ef519986b24f1c950db648a76d"
reg=RES/"fidelity-isolation-regressions-20261009-v8.json"
tests=read(reg)
assert tests["status"]=="PASS" and tests["count"]==tests["passed"]==32
assert tests["historical_v7_and_v6_reports_unchanged"] is True

pos=read(R9/"feedback-guest-mouse-trace.json")
neg=read(R10/"feedback-guest-mouse-trace.json")
assert pos["status"]=="FEEDBACK_CALIBRATED_NEWGAME_CLICK_AND_MOVIE_SKIP_SENT"
assert pos["button_press_released"] is True and pos["movie_skip_space_sent"] is True
assert len(pos["cursor_feedback_observations"])==3
observed=[(x["cursor"]["x"],x["cursor"]["y"]) for x in pos["cursor_feedback_observations"]]
assert observed==[(-2,233),(198,421),(316,421)],observed
assert pos["cursor_feedback_observations"][-1]["cursor"]["NewGame_click_allowed"] is True
assert neg["status"]=="FEEDBACK_INPUT_BINDING_OR_CALIBRATION_ERROR"
assert neg["error"]=="IsolationError:CURSOR_FEEDBACK_POSITION_UNKNOWN"
assert not neg["button_press_released"] and not neg["movie_skip_space_sent"]
assert neg["cursor_feedback_observations"][0]["cursor"]["status"]=="CURSOR_POSITION_UNKNOWN_FAIL_CLOSED"

run=read(R9/"result.json")
assert run["exit_code"]==0 and run["diagnostic_capture_status"]=="PASS"
assert run["registered_target"]["classification"]=="DOSBOX_X_REUSED_HASH_PINNED_PRIOR_ART"
assert run["game_source_binding"]["status"]=="PASS_SOURCE_BOUND"
assert Path(run["game_source_binding"]["config_game_root"])==(R/"source"/"Zork Nemesis")
master_file=R9/"fidelity-isolated"/"capture"/"capture-attestation.json"
master=read(master_file)
assert verify_bounded_wgc_sequence_v2(master_file.parent,master)["verified_frames"]==5
assert master["pid"]==run["runtime_identity"]["pid"]
assert master["hwnd"]==run["runtime_window"]["hwnd"]
assert master["creation_ticks_100ns"]==run["runtime_identity"]["creation_ticks_100ns"]
assert [x["requested_at_seconds"] for x in master["frames"]]==[35,43,54,66,73]
assert master["frames"][3]["sha256"]==master["frames"][4]["sha256"]
assert master["remote_desktop_capture_authority"] is False
assert len(pos["supervised_peer_binding"])>=3
assert all(x["result"]["runtime_pid"]==master["pid"] and
 x["result"]["lease_epoch"]==master["run_token"] and
 x["result"]["executable_sha256"]==master["executable_sha256"]
 for x in pos["supervised_peer_binding"])

original_courtyard=R9/"original-native-TA30-courtyard-fixedviewport-512x320.png"
assert original_courtyard.is_file()
native_pixel=read(R9/"native-vs-R29-temple-technical-comparison.json")
assert native_pixel["native_original_viewport_sha256"]==sha256(original_courtyard)
assert native_pixel["retail_Godot_gameplay_fidelity"]=="HOLD"
assert native_pixel["source_scene_hypothesis"].startswith("TEMPLE/TA30")

gate=read(RES/"original-newgame-cursor-gate-canary-v8.json")
feedback=read(RES/"native-original-cursor-feedback-fixtures-v8.json")
assert gate["status"]=="PASS_TWO_POSITIVES_TWO_NEGATIVES"
assert feedback["status"]=="PASS_ORIGINAL_POSITIVE_AND_TWO_CLIPPED_NEGATIVE_FRAMES"
r8=read(RES/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"/"cursor-guarded-original-newgame-input-trace.json")
assert r8["status"]=="SAFE_NO_CLICK_CURSOR_OUTSIDE_NEWGAME"
assert not r8["click_sent"] and not r8["space_sent"]
r7=read(RES/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"newgame-spacebar-fivepoint-observation.json")
assert len({x["sha256"] for x in r7["frames"][1:]})==1
replay=read(R9/"feedback-gameplay-original-observation-v8.json")
assert replay["preclick_frame_authorized"] is True
assert replay["movie_skip_space_sent"] is True

frozen=CP/"framework-vnext-policies.json"
backup=R/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
assert sha256(frozen)==sha256(backup)==old["framework"]["frozen_phase1_policy_sha256"]
pinned=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
assert sha256(pinned)==old["openzork"]["pinned_save_sha256"]
original_tgz=R/"source"/"Zork Nemesis"/"DATA2"/"ZASSETS"/"CONSERV"/"VB30S11C.TGA"
assert sha256(original_tgz)==old["openzork"]["original_game_data_TGZ_sha256"]

source_exe=R/"source"/"Zork Nemesis"/"ZORKDOS.EXE"
assert source_exe.is_file(),"AUTH_ORIGINAL_DOS_PROGRAM_NOT_FOUND"
artifacts=[
 CP/"FIDELITY_RUNTIME_ISOLATION_V8.md",
 CP/"fidelity_runtime_worker_v1.py",
 CP/"fidelity_capture_sequence_v1.py",
 CP/"fidelity_capture_sequence_v2.py",
 CP/"fidelity_original_cursor_gate_v1.py",
 CP/"fidelity_native_cursor_feedback_v1.py",
 CP/"fidelity_mcp_peer_attestation_v8.py",
 CP/"fidelity_target_binding_v1.py",
 CP/"fidelity_runtime_isolation_v1.py",
 CP/"orch_k003.py",
 CP/"schemas"/"orch-k003-job.schema.json",
 CP/"fidelity-runtime-target-registry.v7.json",
 CP/"test_capture_schedule_v2_v8.py",
 CP/"test_original_newgame_cursor_gate_v8.py",
 CP/"test_native_cursor_feedback_v8.py",
 CP/"test_mcp_tcp_peer_attestation_v8.py",
 CP/"test_native_zork_r9_replay_gate_v8.py",
 CP/"test_fidelity_runtime_regressions_v8.py",
 CP/"controller_zork_cursor_feedback_r9_v8.py",
 CP/"controller_zork_cursor_feedback_r10_v8.py",
 CP/"analyze_original_zork_feedback_r9_v8.py",
 CP/"compare_native_zork_courtyard_to_r29_v8.py",
 R/"orchestrator"/"capture-worker"/"capture_window_wgc.exe",
 R/"orchestrator"/"capture-worker"/"capture_process_audio.exe",
 source_exe
]
evidence=[
 prior,reg,
 RES/"original-newgame-cursor-gate-canary-v8.json",
 RES/"native-original-cursor-feedback-fixtures-v8.json",
 RES/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"newgame-spacebar-fivepoint-observation.json",
 RES/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"/"cursor-guarded-original-gameplay-observation-v8.json",
 RES/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"/"left-edge-cursor-probe-v8.json",
 R9/"feedback-guest-mouse-trace.json",
 R9/"feedback-gameplay-original-observation-v8.json",
 R9/"native-vs-R29-temple-technical-comparison.json",
 R9/"native-zork-feedback-fivepoint-contact.png",
 R9/"native-vs-previous-TA30-oracle-godot.png",
 master_file,
 original_courtyard,
 R10/"feedback-guest-mouse-trace.json",
 R10/"cursor-missing-frame-diagnostic.json",
 RES/"openzork-native-dosboxx-extended-newgame-20261009-r6"/"authenticated-MCP-original-native-input-trace.json",
 RES/"openzork-native-dosboxx-mcp-new-game-click-20261009-r5"/"native-newgame-click-analysis.json",
 RES/"fidelity-isolation-regressions-20261009-v7-r3.json",
 R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-R10-MASKED-DIFF-r30"/"R30_MASKED_ALIGNMENT_CHECKPOINT.json"
]
def fp(files):
 result=[]
 for path in files:
  path=Path(path)
  assert path.is_file(),str(path)
  result.append({"path":str(path.relative_to(R)),"sha256":sha256(path),
   "bytes":path.stat().st_size})
 return result
windows=gui_conflicts()
ckpt={
 "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v8",
 "created_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"NATIVE_ZORKDOS_NEWGAME_SPACE_FIRST_COURTYARD_TECH_PASS_REPEATABILITY_HOLD_FIDELITY_HOLD",
 "previous_checkpoint_sha256":sha256(prior),
 "v8_regression":{"status":"PASS","passed":32,"total":32,"hash":sha256(reg)},
 "framework":{
  "managed_interactive_gui_slots":1,"total_heavy_slots":3,
  "global_named_mutex":"Global\\OpenRemaster_HomePC_InteractiveFidelity_v1",
  "process_TCP_peer_PID_creation_executable_sha_lease":"PASS",
  "source_only_native_WGC_capture":"PASS",
  "process_loopback_audio_previous_v7":"PASS_TECHNICAL",
  "RDC_stream_not_fidelity_authority":True,
  "out_of_band_debugger_controller":"EXPERIMENTAL_NOT_PRODUCTION_ADAPTER",
  "frozen_policy_sha256":sha256(frozen)},
 "original_ZORKDOS":{
  "original_game_EXE_sha256":sha256(source_exe),
  "source_root":str(R/"source"/"Zork Nemesis"),
  "original_emulator_registered_hash":master["executable_sha256"],
  "authenticated_PID":master["pid"],
  "authenticated_HWND":master["hwnd"],
  "authenticated_creation_ticks":master["creation_ticks_100ns"],
  "input_trace":"MOUSE_NEWGAME_CLICK_PLUS_SPACE_SKIP_ORIGINAL_FMV",
  "native_courtyard_reached":True,
  "stable_native_frame_offsets_seconds":[66,73],
  "stable_native_frame_hash":master["frames"][3]["sha256"],
  "native_courtyard_512x320_viewport_sha256":sha256(original_courtyard),
  "external_controller_feedback_iterations":3,
  "source_cursor_positive_and_negative_controls":"PASS",
  "r7_wrong_cursor_game_menu_not_advanced":True,
  "r8_wrong_cursor_guard_no_click":True,
  "r9_actual_native_first_courtyard":"TECHNICAL_PASS",
  "r10_invisible_pointer_guard_no_click":True,
  "reproducible_original_action_sequence":"HOLD",
  "exact_original_native_scene_ID_pose":"NOT_INDEPENDENTLY_VERIFIED",
  "native_vs_R29_scummvm_exploratory_MAE":native_pixel["comparison_metrics"]["native_ZORKDOS_vs_prior_ScummVM"]["MAE_0_255"],
  "native_vs_R29_Godot_exploratory_MAE":native_pixel["comparison_metrics"]["native_ZORKDOS_vs_prior_Godot"]["MAE_0_255"],
  "same_action_Godot_replay":"NOT_EXECUTED",
  "candidate_audio_and_state_fidelity":"NOT_VERIFIED",
  "release_FIDELITY_VERIFIED":"HOLD"
 },
 "homepc_snapshot":{
  "active_console_session":active_console_session(),
  "checkpoint_worker_session":process_session(__import__("os").getpid()),
  "unmanaged_game_windows_detected":len(windows),
  "unmanaged_PIDs_detected":len({x["pid"] for x in windows}),
  "by_GUI_executable":dict(Counter(Path(x["executable"]).name for x in windows)),
  "legacy_processes_terminated":0
 },
 "original_corpus_immutability":{
  "native_ZORKDOS_EXE_sha256":sha256(source_exe),
  "pinned_VB30_saved_state_sha256":sha256(pinned),
  "native_VB30_source_TGZ_sha256":sha256(original_tgz),
  "Phase1_policy_sha256":sha256(frozen),
  "source_writes_by_this_migration":"NONE"
 },
 "artifacts":fp(artifacts),
 "evidence":fp(evidence),
 "rehydration_contract":{
  "hash_provenance":"REQUIRE_ALL_MANIFEST_HASHES",
  "restore_recipe":[
   "Verify all artifact/evidence hashes and frozen original phase 1 policy.",
   "Use known registered DOSBox-X EXE and read-only ZORKDOS game corpus in a NEW private per-run overlay.",
   "Run v8 non-destructive regression 32 cases to a new uniquely named report; preserve old reports.",
   "Launch only through ORCH-K003 GUI lease and verify native WGC producer source/process bound.",
   "Authenticate localhost TCP process PID/creation/executable hash/GUI lease on every pre-input phase.",
   "Use recovered source cursor WGC position gate, bounded correction and no-click if pointer not visible.",
   "Reproduce r9 original NewGame -> Space -> Courtyard and negative fixture r10.",
   "Do not award PLAYABLE or FIDELITY_VERIFIED without independent native-original vs Godot state/input/audio replay validation."
  ],
  "smoke_test":"32_NONDESTRUCTIVE_REGRESSIONS_PASS",
  "resulting_fingerprint":"VERIFIED_SHA256_ARTIFACTS_AND_SOURCE_GAME"}
}
out=RES/"fidelity-runtime-isolation-checkpoint-20261009-v8.json"
if out.exists():raise RuntimeError("V8_CHECKPOINT_ALREADY_EXISTS_NO_OVERWRITE")
out.write_text(json.dumps(ckpt,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":ckpt["schema"],"status":ckpt["status"],
 "regressions":32,"artifact_hashes":len(ckpt["artifacts"]),
 "evidence_hashes":len(ckpt["evidence"]),
 "native_courtyard_sha256":ckpt["original_ZORKDOS"]["stable_native_frame_hash"],
 "input_repeatability":"HOLD","godot_fidelity":"HOLD",
 "unmanaged_gui_windows":ckpt["homepc_snapshot"]["unmanaged_game_windows_detected"],
 "checkpoint":str(out),"checkpoint_sha256":sha256(out)},ensure_ascii=False))
