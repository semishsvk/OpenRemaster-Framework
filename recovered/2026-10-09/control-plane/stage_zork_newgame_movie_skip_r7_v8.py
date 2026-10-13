"""Original ZORKDOS New Game / skip-FMV positive against no-skip r6 control.
Registered DOSBox-X, shared game corpus mounted read-only, external loopback input
with exact PID, creation ticks, executable hash and GUI lease attestation.
Only project private staging and job JSON are created; no game launched here.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
prior=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/"openzork-native-dosboxx-extended-newgame-20261009-r6.json"
oldconf=R/"work"/"OpenZork"/"staging"/"dosboxx-extended-newgame-20261009-r6"/"NATIVE_ZORK_EXTENDED_NEWGAME.conf"
assert prior.is_file() and oldconf.is_file()
rid="openzork-native-dosboxx-newgame-skipintro-20261009-r7"
stage=R/"work"/"OpenZork"/"staging"/rid
assert not stage.exists(),"R7_WORKSPACE_ALREADY_EXISTS"
stage.mkdir(parents=True)
config=stage/"ZORKDOS_NATIVE_NEWMOVIE_SKIP.conf"
text=oldconf.read_text(encoding="utf-8")
assert text.count("mcp_server=59095")==1
assert "debugbox" not in text.lower() and "autotype -w 8" in text.lower()
config.write_text(text.replace("mcp_server=59095","mcp_server=59096"),encoding="utf-8")
job=json.loads(prior.read_text(encoding="utf-8"))
job["job_id"]=rid
job["task"]="NativeZorkDOSMenuNewGameThenGuestSpacebarSkipOriginalFMV"
job["execution"]["config_source"]=str(config)
job["execution"]["capture_schedule_seconds"]=[35,43,54,66,73]
job["execution"]["capture_schedule_contract"]="v2_extended"
job["execution"]["timeout_seconds"]=110
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job["inputs"][0]={"path":str(config),"sha256":sha(config)}
out=prior.with_name(rid+".json")
assert not out.exists(),"R7_JOB_ALREADY_EXISTS"
out.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
record={"schema":"OpenZork.NativeOriginalFMVSkipExperimentPlan.v1",
"status":"STAGED_UNEXECUTED",
"job_id":rid,"exact_registered_exe_sha256":job["inputs"][1]["sha256"],
"private_config_sha256":sha(config),"corpus_read_only":True,
"original_game":"ZORKDOS.EXE","normal_run_no_debugger_pause":True,
"original_game_manual":"SPACEBAR_SKIPS_MOVIES",
"loopback_port":59096,
"input_events":[
 {"at_s_approx":40,"type":"DOSBOX_GUEST_MOUSE_RELATIVE_Y_PLUS_110"},
 {"at_s_approx":41,"type":"DOSBOX_GUEST_MOUSE_LEFT_DOWN"},
 {"at_s_approx":42,"type":"DOSBOX_GUEST_MOUSE_LEFT_UP"},
 {"at_s_approx":57,"type":"DOSBOX_GUEST_KEYBOARD_SPACE_DOWN_0x39"},
 {"at_s_approx":58,"type":"DOSBOX_GUEST_KEYBOARD_SPACE_UP_0xB9"}
],
"capture_schedule_seconds":job["execution"]["capture_schedule_seconds"],
"negative_control_no_space":"openzork-native-dosboxx-extended-newgame-20261009-r6",
"original_vs_reconstruction_replay":"NOT_TESTED",
"fidelity_verified":False,"job_file":str(out)}
plan=stage/"skip-FMV-plan.json"
plan.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED","job":str(out),
"port":59096,"capture_offsets":record["capture_schedule_seconds"],
"control":"r6_NO_MOVIE_SKIP","plan":str(plan)}))
