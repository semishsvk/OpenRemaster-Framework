"""Sealed, additive Fidelity Runtime Isolation v7 checkpoint.
Read-only verification of old evidence/source. Creates only a new v7 JSON manifest.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,platform,stat
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts,active_console_session,process_session
from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
from fidelity_target_binding_v1 import registry,validate_registered_target,validate_game_config_binding
from fidelity_process_wide_preflight_v7 import console_runtime_process_conflicts

R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
RES=R/"runtime-test"/"results"
SOURCE=R/"source"
SAVE_DIR=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"
GOLD=RES/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
PINNED_RUN=RES/"openzork-pinned-vb30-supervised-sequence-v7-r1"
G2=RES/"openzork-vb30-1058-godot-headless-20261009-r2"
G3=RES/"openzork-vb30-1058-godot-headless-20261009-r3"
REPLAY=RES/"openzork-vb30-scene-hotspot-headless-20261009-r1"

def read_json(path):
    file=Path(path)
    if not file.is_file():raise FileNotFoundError(str(file))
    return json.loads(file.read_text(encoding="utf-8-sig"))

old_checkpoint=RES/"fidelity-runtime-isolation-checkpoint-20261009-v6.json"
v6=read_json(old_checkpoint)
assert v6["schema"]=="OpenRemaster.FidelityRuntimeIsolationCheckpoint.v6"
old_v6_integrity=RES/"fidelity-checkpoint-v6-integrity-audit-20261009.json"
assert read_json(old_v6_integrity)["status"]=="PASS"
regression=RES/"fidelity-isolation-regressions-20261009-v7-r3.json"
r=read_json(regression)
assert r["status"]=="PASS" and r["count"]==r["passed"]==27
assert r["historical_reports_unchanged"] is True

frozen=CP/"framework-vnext-policies.json"
frozen_backup=R/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
assert sha256(frozen)==sha256(frozen_backup)==v6["framework"]["original_frozen_policy_sha256"]
corpus=SOURCE/"Zork Nemesis"/"DATA2"/"ZASSETS"/"CONSERV"/"VB30S11C.TGA"
assert sha256(corpus)=="f31f6892ad01491608af54941b1851711ccf9c9e3c853859a6e04ff411c13cfe"
save=SAVE_DIR/"znemesis.000"
pmanifest=read_json(SAVE_DIR/"pinned-save-manifest.json")
assert sha256(save)==pmanifest["pinned_sha256"]
assert sha256(save)=="3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc"
assert not(save.stat().st_mode & stat.S_IWRITE)

registry_doc=registry()
assert registry_doc["target_count"]==4
executable=SOURCE/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
scum=validate_registered_target("OpenZork","scummvm",executable)
assert scum["classification"]=="SCUMMVM_CROSS_VALIDATION_NOT_NATIVE_DOS"

target_result=read_json(PINNED_RUN/"result.json")
target_receipt=read_json(PINNED_RUN/"control-receipt.json")
target_validator=read_json(PINNED_RUN/"validation-result.json")
target_acceptance=read_json(PINNED_RUN/"acceptance-result.json")
assert target_receipt["status"]=="BLOCKED"
assert target_validator["status"]==target_acceptance["status"]=="FAIL"
assert target_result["status"]=="BLOCKED"
assert target_result["diagnostic_capture_status"]=="PASS" and target_result["exit_code"]==0
assert target_result["game_source_binding"]["status"]=="PASS_SOURCE_BOUND"
assert target_result["game_source_binding"]["config_game_root"]==str(SOURCE/"Zork Nemesis")
assert target_result["registered_target"]["executable_sha256"]==scum["executable_sha256"]
seed_materialization=target_result["save_seed_materialization"]["entries"]
assert len(seed_materialization)==1
seed_item=seed_materialization[0]
assert seed_item["source_kind"]=="PINNED_EVIDENCE"
assert seed_item["seed_scene"]=="vb30" and seed_item["seed_view"]==1058
assert sha256(seed_item["private_copy_path"])==sha256(save)

capture_dir=PINNED_RUN/"fidelity-isolated"/"capture"
master_path=capture_dir/"capture-attestation.json"
master=read_json(master_path)
verified=verify_bounded_wgc_sequence(capture_dir,master)
assert verified["verified_frames"]==3
frames=master["frames"]
assert [x["requested_at_seconds"] for x in frames]==[3,8,14]
assert len({x["sha256"] for x in frames})==1
assert master["pid"]==target_result["runtime_identity"]["pid"]
assert master["hwnd"]==target_result["runtime_window"]["hwnd"]
assert master["remote_desktop_capture_authority"] is False
assert master["audio_backend"]=="process_loopback"
assert len(master["audio"])==1
audio_path=capture_dir/master["audio"][0]["path"]
assert sha256(audio_path)==master["audio"][0]["sha256"]

cursor=read_json(PINNED_RUN/"pinned-vb30-cursor-attribution.json")
assert cursor["status"]=="CURSOR_RESIDUAL_ATTRIBUTED_DIAGNOSTIC_ONLY"
assert cursor["masked_png_equal"] is True
assert cursor["pixels_changed_outside_post_hoc_regions"]==0
assert cursor["full_mask_is_independently_predeclared"] is False
assert cursor["pixel_fidelity_promoted"] is False

pose=read_json(GOLD/"vb30-save-scene-pose-and-decoder-v6.json")
assert pose["location_key"]=="VB30" and pose["view_coordinate"]==1058
assert pose["decoded_ppm_matches_preexisting"] is True
godot_comparison=read_json(G2/"vb30-matched-original-vs-godot-technical-comparison.json")
assert godot_comparison["cpu_projection_exact_match"] is True
assert godot_comparison["retail_fidelity"]=="HOLD"
repeat=read_json(G3/"vb30-repeatable-static-view-checkpoint.json")
assert repeat["exact_engine_png_identical"] is True
hotspot=read_json(REPLAY/"hotspot-runtime-replay-evidence.json")
assert hotspot["status"]=="ACTUAL_GODOT_RUNTIME_STRUCTURAL_HOTSPOT_REPLAY_PASS_FIDELITY_HOLD"
assert len(hotspot["scene_transitions"])==2

target_test=read_json(RES/"fidelity-runtime-target-binding-v7-canary.json")
assert target_test["status"]=="PASS" and target_test["negative_rejection_tests"]==9
wmi_test=read_json(RES/"fidelity-process-wide-guard-canary-v7.json")
assert wmi_test["status"]=="PASS" and wmi_test["query_failure_fail_closed"]
wmiaudit=read_json(RES/"fidelity-process-wide-contamination-audit-v7-r2.json")
assert wmiaudit["schema"]=="OpenRemaster.ProcessWideGUIContaminationAudit.v2"
assert wmiaudit["status"]=="READ_ONLY_COMPLETE"
corrected=read_json(RES/"fidelity-process-audit-supersession-v7.json")
assert corrected["status"]=="INITIAL_ZERO_PROCESS_REPORT_INVALID_SUPERSEDED_BY_R2"

original_only=RES/"openzork-save-scene-pose-inventory-v7.json"
saves=read_json(original_only)
assert not any(x.get("scene")=="vb20" for x in saves["items"])
assert not any(x.get("scene")=="vb30" and x.get("view")==364 for x in saves["items"])

artifacts=[
 CP/"FIDELITY_RUNTIME_ISOLATION_V7.md",
 CP/"fidelity-runtime-target-registry.v7.json",
 CP/"fidelity_target_binding_v1.py",
 CP/"fidelity_process_wide_preflight_v7.py",
 CP/"fidelity_runtime_worker_v1.py",
 CP/"fidelity_runtime_isolation_v1.py",
 CP/"fidelity_local_capture_wgc_v1.py",
 CP/"fidelity_local_audio_loopback_v1.py",
 CP/"fidelity_capture_sequence_v1.py",
 CP/"fidelity_seed_saves_v1.py",
 CP/"orch_k003.py",
 CP/"validator.py",
 CP/"fidelity_scene_pair_guard_v1.py",
 CP/"test_fidelity_runtime_target_binding_v7.py",
 CP/"test_fidelity_process_wide_preflight_v7.py",
 CP/"test_fidelity_runtime_regressions_v7_r3.py",
 CP/"verify_pinned_vb30_supervised_capture_v7.py",
 CP/"attribute_pinned_crossrun_cursor_delta_v7.py",
 CP/"audit_process_owner_session_v7_r2.py",
 CP/"stage_openzork_pinned_runtime_validation_v7.py",
 CP/"verify_fidelity_checkpoint_v6_integrity.py",
 R/"orchestrator"/"capture-worker"/"capture_window_wgc.exe",
 R/"orchestrator"/"capture-worker"/"capture_process_audio.exe"
]
evidence=[
 old_checkpoint,
 old_v6_integrity,
 regression,
 RES/"fidelity-runtime-target-binding-v7-canary.json",
 RES/"fidelity-process-wide-guard-canary-v7.json",
 RES/"fidelity-process-wide-contamination-audit-v7-r2.json",
 RES/"fidelity-process-audit-supersession-v7.json",
 RES/"openzork-save-scene-pose-inventory-v7.json",
 SAVE_DIR/"pinned-save-manifest.json",
 SAVE_DIR/"pinned-pose-reverification.json",
 save,
 PINNED_RUN/"result.json",
 PINNED_RUN/"control-receipt.json",
 master_path,
 audio_path,
 PINNED_RUN/"pinned-capture-evidence-v7.json",
 PINNED_RUN/"pinned-vb30-cursor-attribution.json",
 PINNED_RUN/"cursor-template-localization-v7.json",
 GOLD/"vb30-save-scene-pose-and-decoder-v6.json",
 G2/"vb30-matched-original-vs-godot-technical-comparison.json",
 G3/"vb30-repeatable-static-view-checkpoint.json",
 REPLAY/"hotspot-runtime-replay-evidence.json"
]
def entries(paths):
    result=[]
    for p in paths:
        if not p.is_file():raise FileNotFoundError(str(p))
        result.append({"path":str(p.relative_to(R)),"sha256":sha256(p),"bytes":p.stat().st_size})
    return result
now=gui_conflicts()
allproc=console_runtime_process_conflicts()
godot_fingerprint=read_json(G3/"result.json")["fingerprint"]
record={
 "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v7",
 "status":"PROJECT_BOUND_ORIGINAL_SCENE_CAPTURE_AND_GODOT_STATIC_REPLAY_TECHNICAL_PASS_FULL_FIDELITY_HOLD",
 "sealed_utc":datetime.now(timezone.utc).isoformat(),
 "prior_v6_checkpoint_sha256":sha256(old_checkpoint),
 "v6_historical_integrity":"38_OF_38_PASS_BEFORE_V7_MUTATION",
 "current_regression_tests":{"status":"PASS","count":27,"evidence_sha256":sha256(regression)},
 "framework":{
  "managed_gui_slots":1,"max_heavy_lanes":3,
  "global_mutex":"Global\\OpenRemaster_HomePC_InteractiveFidelity_v1",
  "exact_project_runtime_corpus_registration":True,
  "registered_targets":registry_doc["target_count"],
  "strict_hidden_runtime_process_preflight":True,
  "godot_headless_non_GUI_allowed":True,
  "process_wide_query_failure":"BLOCKED",
  "remote_desktop_video_is_fidelity_authority":False,
  "direct_shell_execution_outside_ORCH_protected":False,
  "frozen_phase1_policy_sha256":sha256(frozen)},
 "openzork":{
  "original_saved_scene":"CONSERV/VB30@1058",
  "pinned_save_sha256":sha256(save),
  "original_game_data_TGZ_sha256":sha256(corpus),
  "source_scene_location_verified":True,
  "private_supervised_SCUMMVM_registered_and_source_bound":True,
  "pinned_save_copied_with_hash_and_LOC":True,
  "supervised_original_frames_three_identical":True,
  "original_audio_process_loopback":"TECHNICAL_PASS",
  "across_two_original_runs_full_frame_exact":False,
  "cursor_difference_post_hoc_mask_outside_pixels_changed":0,
  "cursor_mask_independent_fidelity_authority":False,
  "godot_real_runtime_static_repeatable_two_runs":True,
  "godot_vs_source_cpu_pixels_exact":True,
  "godot_internal_hotspot_state_route":"STRUCTURAL_PASS_ONLY",
  "original_native_DOS_guest_mouse_replay":"BLOCKED_UNVERIFIED",
  "original_VB20_or_second_VB30_save_reference":"NOT_AVAILABLE_IN_BOUNDED_INVENTORY",
  "original_vs_godot_action_state_audio_replay":"NOT_VERIFIED",
  "release_fidelity":"HOLD"},
 "homepc_snapshot":{
  "windows_visible":len(now),
  "relevant_GUI_processes":len(allproc),
  "unmanaged_process_cleanup":"NOT_PERFORMED",
  "GUI_types":dict(Counter(Path(p["executable"]).name for p in allproc)),
  "user_active_session":active_console_session(),
  "checkpoint_worker_session":process_session(__import__("os").getpid())},
 "runtime_environment_fingerprint":{
  "os":platform.platform(),
  "godot_runtime":godot_fingerprint,
  "scummvm_binary_sha256":scum["executable_sha256"],
  "capture_video_producer_sha256":sha256(R/"orchestrator"/"capture-worker"/"capture_window_wgc.exe"),
  "capture_audio_producer_sha256":sha256(R/"orchestrator"/"capture-worker"/"capture_process_audio.exe")},
 "artifacts":entries(artifacts),
 "evidence":entries(evidence),
 "rehydration_contract":{
  "inputs_hashes_recorded":True,
  "runtime_fingerprint_recorded":True,
  "restore_recipe":[
    "Verify every artifact and evidence SHA-256 before treating checkpoint as current.",
    "Verify the frozen framework original policy and pinned ZNSG save SHA-256 plus VB30@1058 LOC.",
    "Re-run the versioned 27 test suite into a NEW unique report rather than overwriting historical results.",
    "Re-commission unknown project/EXE/corpus hashes before any new managed original GUI launch.",
    "Create a new unique ScummVM original diagnostic job from the pinned save, with the global mutex and per-run private directories.",
    "Confirm original local WGC and process-loopback attestations and exact registered runtime game root.",
    "Rehydrate the private headless Godot project; rerun same view and assert pixel-repeatability and scene-pair guard.",
    "Keep full game fidelity HOLD until matched original vs candidate input/state/audio/replay validation passes."],
  "smoke_test":"V7_CORE_AND_SOURCE_TARGET_REGRESSION_27_OF_27_PASS",
  "resulting_fingerprint":"ALL_LISTED_ARTIFACT_AND_EVIDENCE_HASHES"},
 "next_gate":"NATIVE_DOS_EMULATED_INPUT_OR_APPROVED_ORIGINAL_ACTION_TRACE_FOR_MULTI_SCENE_COMPARISON"}
path=RES/"fidelity-runtime-isolation-checkpoint-20261009-v7.json"
if path.exists():raise RuntimeError("V7_CHECKPOINT_ALREADY_EXISTS_NO_OVERWRITE")
path.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":record["schema"],"status":record["status"],
 "regression_pass":27,"artifact_count":len(artifacts),"evidence_count":len(evidence),
 "processes_while_sealing":len(allproc),"windows_while_sealing":len(now),
 "frozen_policy_sha256":record["framework"]["frozen_phase1_policy_sha256"],
 "checkpoint":str(path),"checkpoint_sha256":sha256(path)},ensure_ascii=False))
