"""V6 canonical evidence checkpoint, read-only revalidation of immutable corpus,
Godot runs, scene pairing, legacy input guard and prior frozen framework policy.
Creates only checkpoint JSON under runtime-test/results.
"""
from datetime import datetime,timezone
from pathlib import Path
from collections import Counter
import json,hashlib
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts,active_console_session,process_session

R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
RES=R/"runtime-test"/"results"
GOLD=RES/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
G2=RES/"openzork-vb30-1058-godot-headless-20261009-r2"
G3=RES/"openzork-vb30-1058-godot-headless-20261009-r3"
REPLAY=RES/"openzork-vb30-scene-hotspot-headless-20261009-r1"

def require_json(p):
 if not p.is_file():raise FileNotFoundError(str(p))
 return json.loads(p.read_text(encoding="utf-8-sig"))

BASE=RES/"fidelity-runtime-isolation-checkpoint-20261009-v5.json"
older=require_json(BASE)
assert older["schema"]=="OpenRemaster.FidelityRuntimeIsolationCheckpoint.v5"
reg_file=RES/"fidelity-isolation-regressions-20261009.json"
reg=require_json(reg_file)
assert reg["status"]=="PASS" and reg["count"]==reg["passed"]==25

pose_file=GOLD/"vb30-save-scene-pose-and-decoder-v6.json"
pose=require_json(pose_file)
assert pose["status"]=="SAVE_LOCATION_AND_TGZ_DECODER_BYTE_MATCH_PASS"
assert pose["location_key"]=="VB30" and pose["view_coordinate"]==1058
assert pose["decoded_ppm_matches_preexisting"] is True
pin_dir=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"
pin_manifest=pin_dir/"pinned-save-manifest.json"
pin_pose_file=pin_dir/"pinned-pose-reverification.json"
drift_file=RES/"openzork-save-provenance-drift-20261009-v6.json"
pinned=require_json(pin_manifest)
pinned_pose=require_json(pin_pose_file)
drift=require_json(drift_file)
save=Path(pinned["pinned_save_path"])
historical_mutable_save=Path(pose["save_path"])
mutable_current_hash=sha256(historical_mutable_save) if historical_mutable_save.is_file() else None
native=Path(pose["location_source_path"])
assert pinned["schema"]=="OpenZork.PinnedSavedStateOracle.v1"
assert pinned_pose["status"]=="PINNED_SAVE_REVERIFIED_VB30_1058"
assert pinned_pose["sha256"]==pose["save_sha256"]
assert sha256(save)==pose["save_sha256"]
assert not (save.stat().st_mode & __import__("stat").S_IWRITE)
assert sha256(native)==pose["location_source_sha256"]
assert sha256(Path(pose["preexisting_ppm_path"]))==pose["preexisting_ppm_sha256"]
assert pose["save_sha256"]=="3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc"
assert pose["location_source_sha256"]=="f31f6892ad01491608af54941b1851711ccf9c9e3c853859a6e04ff411c13cfe"

visual_file=G2/"vb30-matched-original-vs-godot-technical-comparison.json"
visual=require_json(visual_file)
assert visual["status"]=="MATCHED_SCENE_AND_POSE_PIXEL_COMPARISON_COMPLETE_FIDELITY_HOLD"
assert visual["cpu_projection_exact_match"] is True
assert visual["retail_fidelity"]=="HOLD"
metrics=visual["pixel_metrics"]
assert metrics["godot_vs_cpu_prior_projection"]["mae"]==0
assert abs(metrics["godot_vs_scummvm_original_bilinear"]["mae"]-4.95018)<1e-4

repeat_file=G3/"vb30-repeatable-static-view-checkpoint.json"
rep=require_json(repeat_file)
assert rep["status"]=="REAL_GODOT_REPEATABLE_PIXEL_IDENTICAL_MATCHED_SCENE_TECHNICAL_PASS_FIDELITY_HOLD"
assert rep["exact_engine_png_identical"] is True
assert rep["exact_engine_pixels_identical"] is True
r2=G2/"engine-vb30-1058.png"
r3=G3/"engine-vb30-1058.png"
assert r2.is_file() and r3.is_file() and r2.read_bytes()==r3.read_bytes()
assert sha256(r2)=="54a47d3ff3313369d4cff545cd83c8a53a1fd7515569f16b5a01885190f4481e"

scene_file=G2/"vb30-original-godot-scene-pair-guard.json"
pair=require_json(scene_file)
assert pair["status"]=="SCENE_PAIR_TECHNICAL_PASS_NEGATIVE_MISMATCHES_BLOCKED"
assert pair["scene_pose"]["scene"]=="VB30" and pair["scene_pose"]["view"]==1058
assert pair["scene_pose"]["fidelity_verified"] is False
assert len(pair["negative_cases"])==4

logic_file=REPLAY/"hotspot-runtime-replay-evidence.json"
logic=require_json(logic_file)
assert logic["status"]=="ACTUAL_GODOT_RUNTIME_STRUCTURAL_HOTSPOT_REPLAY_PASS_FIDELITY_HOLD"
assert logic["first_frame_exact_matches_independent_godot_run"] is True
assert logic["original_source_gd_files_unchanged"] is True
assert len(logic["scene_transitions"])==2
assert logic["external_mouse_key_input_replay"]=="NOT_RUN"
assert logic["actual_engine_frame_sha256"][0]["sha256"]==sha256(r2)

legacy_report_file=RES/"unmanaged-gui-entrypoint-audit-v6.json"
legacy=require_json(legacy_report_file)
assert legacy["state"]=="READ_ONLY" and legacy["affected_scripts"]>=52
guard_report_file=RES/"legacy-gui-executable-admission-canary-v6.json"
guard=require_json(guard_report_file)
assert guard["status"]=="PASS" and guard["dangerous_scripts_executed"]==0

orig_policy=CP/"framework-vnext-policies.json"
backup_policy=R/"orchestrator"/"backups"/"fidelity-isolation-20261009-v1"/"orchestrator"/"control-plane"/"framework-vnext-policies.json"
assert backup_policy.is_file() and sha256(orig_policy)==sha256(backup_policy)

src_helper=R/"work"/"OpenZork"/"runtime"/"scripts"/"capture_helper.gd"
plan=require_json(REPLAY/"scene-hotspot-replay-plan.json")
assert sha256(src_helper)==plan["original_capture_helper_sha256"]
assert sha256(R/"work"/"OpenZork"/"runtime"/"scripts"/"interactive_runtime.gd")==plan["source_runtime_original_sha256"]

artifacts=[
 "orchestrator/control-plane/FIDELITY_RUNTIME_ISOLATION_V6.md",
 "orchestrator/control-plane/fidelity_legacy_executable_guard_v1.py",
 "orchestrator/control-plane/fidelity_scene_pair_guard_v1.py",
 "orchestrator/control-plane/fidelity_runtime_isolation_v1.py",
 "orchestrator/control-plane/fidelity_runtime_worker_v1.py",
 "orchestrator/control-plane/fidelity_local_capture_wgc_v1.py",
 "orchestrator/control-plane/fidelity_local_audio_loopback_v1.py",
 "orchestrator/control-plane/fidelity_targeted_input_v1.py",
 "orchestrator/control-plane/fidelity_owned_mouse_v1.py",
 "orchestrator/control-plane/fidelity_capture_sequence_v1.py",
 "orchestrator/control-plane/fidelity_seed_saves_v1.py",
 "orchestrator/control-plane/orch_k003.py",
 "orchestrator/control-plane/validator.py",
 "orchestrator/control-plane/capabilities.json",
 "orchestrator/control-plane/test_legacy_executable_gui_guard_v6.py",
 "orchestrator/control-plane/test_vb30_scene_pair_guard_v6.py",
 "orchestrator/control-plane/verify_openzork_vb30_pose_and_decoder_v6.py",
 "orchestrator/control-plane/validate_vb30_godot_vs_scummvm_v6.py",
 "orchestrator/control-plane/verify_vb30_godot_reproducibility_v6.py",
 "orchestrator/control-plane/verify_vb30_headless_hotspot_replay_v6.py",
 "orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py",
 "orchestrator/control-plane/test_readonly_save_seed_v5.py",
 "orchestrator/control-plane/verify_pinned_vb30_scene_pose_v6.py",
 "orchestrator/control-plane/seal_vb30_golden_save_reference_v6.py",
 "orchestrator/control-plane/audit_vb30_save_provenance_drift_v6.py"
]
records=[]
for item in artifacts:
 p=R/item
 if not p.is_file():raise FileNotFoundError(item)
 records.append({"path":item,"sha256":sha256(p),"bytes":p.stat().st_size})
evidence={
 "older_v5":BASE,
 "regression":reg_file,
 "original_saved_pose_TGZ_decoder":pose_file,
 "pinned_golden_save_manifest":pin_manifest,
 "pinned_golden_pose_reverification":pin_pose_file,
 "shared_save_drift_audit":drift_file,
 "scummvm_saved_golden_stability":GOLD/"golden-scene-stability.json",
 "original_godot_pixel_comparison":visual_file,
 "paired_scene_negative_control":scene_file,
 "independent_godot_repeatability":repeat_file,
 "godot_structural_hotspot_replay":logic_file,
 "gui_legacy_static_inventory":legacy_report_file,
 "gui_legacy_interpreter_guard":guard_report_file
}
for name,p in evidence.items():
 if not p.is_file():raise FileNotFoundError(name)
windows=gui_conflicts()
counts=Counter(Path(x["executable"]).name for x in windows)
checkpoint={
 "schema":"OpenRemaster.FidelityRuntimeIsolationCheckpoint.v6",
 "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"VB30_PAIRED_ACTUAL_GODOT_STATIC_VISUAL_AND_HOTSPOT_TECHNICAL_PASS_FIDELITY_HOLD",
 "framework":{
   "managed_interactive_GUI_capacity":1,
   "total_headless_plus_GUI_heavy_capacity_policy":3,
   "native_worker_session0_headless":"PASS",
   "unmanaged_direct_RDC_or_shell_invocations_outside_ORCH":"NOT_PROTECTED_OS_WIDE",
   "routed_executable_runtime_legacy_gui_guard":"NEGATIVE_CANARY_PASS",
   "local_provenance_bound_capture":"WGC_AND_PROCESS_LOOPBACK",
   "RDC_stream_is_fidelity_authority":False,
   "legacy_unsafe_GUI_script_audit_count":legacy["affected_scripts"],
   "original_frozen_policy_sha256":sha256(orig_policy),
   "phase1_frozen_unchanged":True
 },
 "openzork":{
   "original_game_engine":"Native DOSBox original side not same saved-state game replay",
   "golden_original_interpreter":"ScummVM ZVision original game data read only",
   "golden_save_source":"PINNED_HASH_VERIFIED_EVIDENCE_COPY",
   "historical_mutable_save":"DRIFTED_DO_NOT_REUSE",
   "scene_id":"VB30",
   "scene_view":1058,
   "source_asset_native_TGZ_sha256":pose["location_source_sha256"],
   "source_save_sha256":pose["save_sha256"],
   "original_scene_saved_location_independently_decoded":True,
   "source_TGZ_to_recovered_PPM_byte_match":True,
   "golden_scummvm_frames_exactly_repeatable":True,
   "godot_headless_actual_runtime_frames_byte_identical_across_2_runs":True,
   "godot_runtime_against_independent_CPU_source_projection_exact_match":True,
   "godot_vs_ScummVM_source_original_MAE_0_255":metrics["godot_vs_scummvm_original_bilinear"]["mae"],
   "godot_vs_ScummVM_source_original_grayscale_corr":metrics["godot_vs_scummvm_original_bilinear"]["corr"],
   "paired_scene_and_view_contract":"PASS",
   "wrong_temple_TA30_pairing_rejected":True,
   "internal_hotspot_replay":"VB30@1058 > VB20@1058 > VB30@364",
   "structural_logic_runtime_replay_status":"PASS",
   "player_input_replay_original_vs_godot":"NOT_VERIFIED",
   "candidate_audio_equivalence":"NOT_TESTED",
   "full_native_original_DOS_fidelity":"HOLD",
   "playability":"NOT_VERIFIED",
   "release_fidelity":"HOLD"
 },
 "tests":{
   "core_regressions":reg["passed"],
   "regressions_total":reg["count"],
   "original_scene_pose_decoder":"BYTE_MATCH_PASS",
   "scene_pair_guard_negative_fixtures":4,
   "independent_Godot_runtime_runs":2,
   "headless_logic_route_transitions":2,
   "legacy_GUI_guard_static_tests":len(guard["cases"])
 },
 "homepc_current_state":{
   "interactive_console_session":active_console_session(),
   "current_execution_session":process_session(__import__("os").getpid()),
   "preexisting_visible_game_GUI_windows":len(windows),
   "preexisting_game_GUI_PIDs":len({x["pid"] for x in windows}),
   "GUI_process_types":dict(counts),
   "unowned_legacy_process_cleanup":"NOT_ATTEMPTED"
 },
 "source_immutability":{
   "original_game_TGZ_sha256":sha256(native),
   "pinned_golden_save_sha256":sha256(save),
   "pinned_golden_save_readonly":True,
   "historical_mutable_save_current_sha256":mutable_current_hash,
   "historical_mutable_save_authority":False,
   "original_capture_helper_sha256":sha256(src_helper),
   "Phase1_frozen_policy_sha256":sha256(orig_policy),
   "canonical_original_source_writes":"NONE",
   "old_mutable_save_restored_or_overwritten":False
 },
 "artifacts":records,
 "evidence":[{"item":key,"path":str(p),"sha256":sha256(p)} for key,p in evidence.items()],
 "previous_checkpoint_sha256":sha256(BASE),
 "restore_recipe":[
   "Verify all artifacts[].sha256 and evidence[].sha256 before replay.",
   "Run core regression suite at orchestrator/control-plane/test_fidelity_runtime_regressions_v1.py.",
   "Recheck PINNED save LOC VB30@1058, pinned manifest and TGZ recovered PPM byte equality without changing original.",
   "Never rely on the drifted historical mutable staging save as immutable evidence.",
   "Rehydrate imported private Godot project and run unique ORCH-K003 headless render jobs; never override evidence.",
   "Validate Godot byte identical frames and hotspot 2-transition internal runtime route.",
   "Do not grant PLAYABLE, REPLAY_VERIFIED, or FIDELITY_VERIFIED from static or internal-only evidence."
 ],
 "next_critical_gate":"ALIGNED_ORIGINAL_AND_GODOT_ACTION_TRACE_WITH_NATIVE_SOURCE_GAME_AUDIO_AND_VISUAL_COMPARISON"
}
path=RES/"fidelity-runtime-isolation-checkpoint-20261009-v6.json"
if path.exists():raise RuntimeError("CHECKPOINT_V6_ALREADY_EXISTS_NO_OVERWRITE")
path.write_text(json.dumps(checkpoint,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({
 "schema":checkpoint["schema"],
 "status":checkpoint["status"],
 "core_regression_pass":reg["passed"],
 "scene":"VB30@1058",
 "pixel_engine_vs_cpu_exact":True,
 "godot_static_runtime_repeats":2,
 "structural_hotspot_transitions":2,
 "source_vs_Godot_mae":checkpoint["openzork"]["godot_vs_ScummVM_source_original_MAE_0_255"],
 "file_hash_manifest_count":len(records),
 "evidence_item_count":len(checkpoint["evidence"]),
 "remaining_legacy_GUI_PIDs":checkpoint["homepc_current_state"]["preexisting_game_GUI_PIDs"],
 "checkpoint":str(path),"checkpoint_sha256":sha256(path),
 "fidelity":"HOLD"
},ensure_ascii=False))
