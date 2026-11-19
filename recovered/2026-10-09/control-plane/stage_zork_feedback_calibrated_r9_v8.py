"""Original native Zork New Game with bounded 4-step cursor-image feedback calibration.
Only original read-only corpus in registered DOSBox-X, no OS-global cursor/focus.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
prior=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8.json"
conf=R/"work"/"OpenZork"/"staging"/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"/"ZORKDOS_IMAGE_GUARDED_CLICK.conf"
rid="openzork-native-dosboxx-cursor-feedback-newgame-20261009-r9"
stage=R/"work"/"OpenZork"/"staging"/rid
assert not stage.exists() and prior.is_file() and conf.is_file()
stage.mkdir(parents=True)
new=stage/"ZORKDOS_FEEDBACK_CALIBRATED.conf"
s=conf.read_text(encoding="utf-8")
assert s.count("mcp_server=59097")==1
new.write_text(s.replace("mcp_server=59097","mcp_server=59098"),encoding="utf-8")
job=json.loads(prior.read_text(encoding="utf-8"))
job["job_id"]=rid
job["task"]="OriginalZORKDOSImageFeedbackCalibrateThenClickNewGameIfAuthorized"
job["execution"]["config_source"]=str(new)
job["inputs"][0]={"path":str(new),"sha256":hashlib.sha256(new.read_bytes()).hexdigest()}
jf=prior.with_name(rid+".json")
assert not jf.exists()
jf.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
m={"schema":"OpenZork.OriginalCursorFeedbackGameplayExperimentPlan.v1",
 "status":"STAGED_ONLY","job_id":rid,
 "source_read_only":True,"loopback_port":59098,
 "first_guest_motion":"Y_PLUS_110",
 "cursor_feedback":"ORIGINAL_00idleA_SPRITE_IN_LOCAL_WGC",
 "maximum_calibration_steps":4,
 "max_each_guest_positive_axis_delta":200,
 "each_step_requires_new_LOCAL_WGC_AND_OWNER_VERIFICATION":True,
 "click_requires_positive_NewGame_ROI":True,
 "skip_movie_space_requires_successful_click":True,
 "capture_offsets":[35,43,54,66,73],
 "bad_cursor_result":"NO_CLICK_NO_GLOBAL_MOUSE_ACTION",
 "image_guard_fixture_evidence":"native-original-cursor-feedback-fixtures-v8.json",
 "old_fidelity_gate":"HOLD",
 "job":str(jf)}
plan=stage/"feedback-plan.json"
plan.write_text(json.dumps(m,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":m["status"],"run":rid,"port":59098,
"job":str(jf),"max_steps":4,"plan":str(plan)}))
