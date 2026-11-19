"""Independent 2nd original-ZORKDOS feedback-driven New Game/Space run.
Use same immutable controller algorithm, new private job and loopback port;
retains r9 artifacts for independent cross-run state/fidelity comparison.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).parent
prev="openzork-native-dosboxx-cursor-feedback-newgame-20261009-r9"
rid="openzork-native-dosboxx-cursor-feedback-newgame-20261009-r10"
base=R/"work"/"OpenZork"/"staging"/rid
assert not base.exists(),"R10_STAGE_EXISTS"
base.mkdir(parents=True)
prev_conf=R/"work"/"OpenZork"/"staging"/prev/"ZORKDOS_FEEDBACK_CALIBRATED.conf"
orig=prev_conf.read_text(encoding="utf-8")
assert orig.count("mcp_server=59098")==1
conf=base/"ZORKDOS_FEEDBACK_REPEAT.conf"
conf.write_text(orig.replace("mcp_server=59098","mcp_server=59099"),encoding="utf-8")
jobprev=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/(prev+".json")
job=json.loads(jobprev.read_text(encoding="utf-8"))
job["job_id"]=rid
job["task"]="IndependentOriginalZorkDOSFeedbackReplayRepeatability"
job["execution"]["config_source"]=str(conf)
job["inputs"][0]={"path":str(conf),"sha256":hashlib.sha256(conf.read_bytes()).hexdigest()}
jobfile=jobprev.with_name(rid+".json")
if jobfile.exists():raise RuntimeError("R10_JOB_EXISTS")
jobfile.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
source=CP/"controller_zork_cursor_feedback_r9_v8.py"
replay=CP/"controller_zork_cursor_feedback_r10_v8.py"
if replay.exists():raise RuntimeError("R10_CONTROLLER_EXISTS")
text=source.read_text(encoding="utf-8")
assert text.count(prev)==1 and "port=59098" in text
text=text.replace(prev,rid).replace("port=59098","port=59099")
replay.write_text(text,encoding="utf-8")
prior=CP/"analyze_original_zork_feedback_r9_v8.py"
analysis=CP/"analyze_original_zork_feedback_r10_v8.py"
if analysis.exists():raise RuntimeError("R10_ANALYZER_EXISTS")
text=prior.read_text(encoding="utf-8")
assert text.count(prev)==1
analysis.write_text(text.replace(prev,rid),encoding="utf-8")
manifest={
 "schema":"OpenZork.SecondNativeGuestMouseReplayPlan.v1",
 "status":"STAGED_NEW_PRIVATE_RUN_ONLY",
 "repeat_of":prev,"new_run":rid,
 "new_loopback_port":59099,
 "config_sha256":hashlib.sha256(conf.read_bytes()).hexdigest(),
 "controller_sha256":hashlib.sha256(replay.read_bytes()).hexdigest(),
 "registered_executable_sha256":job["inputs"][1]["sha256"],
 "same_image_feedback_code":True,"same_capture_offsets":job["execution"]["capture_schedule_seconds"],
 "canonical_source_read_only":True,"job":str(jobfile),"controller":str(replay),"analyzer":str(analysis),
 "original_vs_Godot_fidelity":"HOLD"}
dest=base/"repeated-replay-plan.json"
dest.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":manifest["status"],"run":rid,
"controller":str(replay),"job":str(jobfile),"port":59099,"plan":str(dest)}))
