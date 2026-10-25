"""Independent native ZORKDOS original New Game / Space / stable courtyard
evidence verification with negative controls r7, r8, r10. Pure read-only audit.
"""
from pathlib import Path
import json,hashlib
from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
from fidelity_original_cursor_gate_v1 import evaluate_original_newgame_cursor
R=Path(__file__).resolve().parents[2]
base=R/"runtime-test"/"results"
pos=base/"openzork-native-dosboxx-cursor-feedback-newgame-20261009-r9"
negdirs={x:base/("openzork-native-dosboxx-"+x) for x in ()}
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
mfile=pos/"fidelity-isolated"/"capture"/"capture-attestation.json"
m=json.loads(mfile.read_text(encoding="utf-8-sig"))
assert verify_bounded_wgc_sequence_v2(mfile.parent,m)["verified_frames"]==5
assert len(m["frames"])==5 and m["frames"][3]["sha256"]==m["frames"][4]["sha256"]
actual=pos/"fidelity-isolated"/"capture"/"samples"/"point-04"/"frame-0001.bmp"
assert h(actual)==m["frames"][3]["sha256"]
trace=json.loads((pos/"feedback-guest-mouse-trace.json").read_text(encoding="utf-8-sig"))
assert trace["status"]=="FEEDBACK_CALIBRATED_NEWGAME_CLICK_AND_MOVIE_SKIP_SENT"
assert trace["button_press_released"] and trace["movie_skip_space_sent"]
assert len(trace["cursor_feedback_observations"])==3
assert trace["cursor_feedback_observations"][-1]["cursor"]["NewGame_click_allowed"]
assert len(trace["supervised_peer_binding"])>=3
assert all(x["result"]["runtime_pid"]==m["pid"] and
           x["result"]["lease_epoch"]==m["run_token"]
           for x in trace["supervised_peer_binding"])
worker=json.loads((pos/"result.json").read_text(encoding="utf-8-sig"))
assert worker["exit_code"]==0 and worker["diagnostic_capture_status"]=="PASS"
assert worker["registered_target"]["classification"]=="DOSBOX_X_REUSED_HASH_PINNED_PRIOR_ART"
assert m["executable_sha256"]==worker["runtime_identity"]["executable_sha256"]
assert m["pid"]==worker["runtime_identity"]["pid"]
assert m["hwnd"]==worker["runtime_window"]["hwnd"]
compare=json.loads((pos/"native-vs-R29-temple-technical-comparison.json").read_text(encoding="utf-8-sig"))
assert compare["status"]=="NATIVE_SOURCE_SAME_SCENE_COMPARISON_COMPUTED_ORIGINAL_GODOT_FIDELITY_HOLD"
assert compare["retail_Godot_gameplay_fidelity"]=="HOLD"
assert compare["native_original_viewport_sha256"]==h(pos/"original-native-TA30-courtyard-fixedviewport-512x320.png")
r7=base/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"
fail7=json.loads((r7/"newgame-spacebar-fivepoint-observation.json").read_text(encoding="utf-8-sig"))
assert len({x["sha256"] for x in fail7["frames"][1:]})==1
r8=base/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"
fail8=json.loads((r8/"cursor-guarded-original-newgame-input-trace.json").read_text(encoding="utf-8-sig"))
assert fail8["status"]=="SAFE_NO_CLICK_CURSOR_OUTSIDE_NEWGAME" and not fail8["click_sent"] and not fail8["space_sent"]
r10=base/"openzork-native-dosboxx-cursor-feedback-newgame-20261009-r10"
fail10=json.loads((r10/"feedback-guest-mouse-trace.json").read_text(encoding="utf-8-sig"))
assert fail10["status"]=="FEEDBACK_INPUT_BINDING_OR_CALIBRATION_ERROR"
assert not fail10["button_press_released"] and not fail10["movie_skip_space_sent"]
assert fail10["error"]=="IsolationError:CURSOR_FEEDBACK_POSITION_UNKNOWN"
registry=R/"orchestrator"/"control-plane"/"fidelity-runtime-target-registry.v7.json"
items=json.loads(registry.read_text(encoding="utf-8-sig"))["entries"]
assert any(x["project"]=="OpenZork" and
 x["executable_sha256"]==m["executable_sha256"] and
 x["classification"]=="DOSBOX_X_REUSED_HASH_PINNED_PRIOR_ART" for x in items)
result={
 "schema":"OpenZork.NativeOriginalSourceInputAndCourtyardVerification.v1",
 "status":"PASS_ORIGINAL_TITLE_NEWGAME_SPACE_STABLE_COURTYARD_TECHNICAL_ONLY",
 "positive_r9":{
  "PID":m["pid"],"HWND":m["hwnd"],
  "executable_sha256":m["executable_sha256"],
  "original_game_start":"ZORKDOS.EXE",
  "verified_cursor_feedback_rounds":3,
  "NewGame_guest_click":True,
  "movie_skip_guest_Spacebar":True,
  "courtyard_66s_and_73s_frame_identical":True,
  "native_viewport_sha256":compare["native_original_viewport_sha256"],
  "original_wgc_manifest_sha256":h(mfile),
  "source_game_read_only":True},
 "negative_r7":"WRONG_CURSOR_TITLE_UNCHANGED",
 "negative_r8":"WGC_INPUT_GUARD_SAFELY_REFUSED_CLICK",
 "negative_r10":"UNLOCATABLE_POINTER_SAFELY_REFUSED_CLICK",
 "same_input_replay_success_across_two_independent_native_runs":False,
 "candidate_Godot_input_replay_equivalence":"NOT_TESTED",
 "native_fidelity_verified":False
}
print(json.dumps({"status":result["status"],
 "stable_original_viewport_sha256":result["positive_r9"]["native_viewport_sha256"],
 "negative_controls":[result["negative_r7"],result["negative_r8"],result["negative_r10"]],
 "repeatability":"HOLD","fidelity":"HOLD"},ensure_ascii=False))
