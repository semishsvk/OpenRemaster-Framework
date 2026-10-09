"""Same original ZORKDOS input/renderer, exclusive HomePC GUI lease; add only one
internally emulated mouse press/release after previously verified move to New Game.
External MCP probe remains diagnostic-only, NOT a production fidelity input oracle.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
root=R/"work"/"OpenZork"/"staging"
old=root/"dosboxx-original-normalrun-mousemove-20261009-r4"/"ZORK_NATIVE_LIVE_MOUSEMOVE.conf"
newroot=root/"dosboxx-original-native-newgame-click-20261009-r5"
if newroot.exists():raise RuntimeError("NATIVE_NEWGAME_STAGE_ALREADY_EXISTS")
newroot.mkdir(parents=True)
data=old.read_text(encoding="utf-8")
assert data.count("mcp_server=59093")==1 and data.count("zorkdos.exe")==1
cfg=newroot/"ZORKDOS_NATIVE_MOUSE_CLICK.conf"
cfg.write_text(data.replace("mcp_server=59093","mcp_server=59094"),encoding="utf-8")
prior=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/"openzork-native-dosboxx-live-mousemove-20261009-r4.json"
job=json.loads(prior.read_text(encoding="utf-8"))
rid="openzork-native-dosboxx-mcp-new-game-click-20261009-r5"
job["job_id"]=rid
job["task"]="OriginalZorkDOSNativeMouseNewGameSingleLeftClickDiagnostic"
job["execution"]["config_source"]=str(cfg)
job["execution"]["capture_schedule_seconds"]=[37,42,44]
job["inputs"][0]={"path":str(cfg),"sha256":hashlib.sha256(cfg.read_bytes()).hexdigest()}
target=prior.with_name(rid+".json")
assert not target.exists()
target.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
record={
 "schema":"OpenZork.NativeZorkDOSNewGameMouseClickExperiment.v1",
 "status":"STAGED_ONLY",
 "project":"OpenZork","run_id":rid,"loopback_debug_port":59094,
 "registered_original_emulator_sha256":job["inputs"][1]["sha256"],
 "original_game_corpus_source":"READ_ONLY",
 "prev_native_mouse_movement_positive":"openzork-native-dosboxx-live-mousemove-20261009-r4",
 "protocol":"DOSBOX_X_GUEST_INTEGRATION_REGISTER_0x804200",
 "sequence":[
  {"at_seconds_approx":40.4,"event":"RELATIVE_MOUSE_Y_PLUS_110"},
  {"at_seconds_approx":40.9,"event":"LEFT_MOUSE_DOWN"},
  {"at_seconds_approx":41.3,"event":"LEFT_MOUSE_UP"}],
 "capture_schedule_seconds":[37,42,44],
 "no_global_mouse_or_host_input":True,
 "guest_new_game_activation_unverified":True,
 "fidelity_gate":"HOLD",
 "job":str(target)}
plan=newroot/"plan.json"
plan.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED","run_id":rid,"port":59094,
 "control_r4":"MOUSE_MOVE_ONLY","r5":"MOUSE_MOVE_AND_SINGLE_CLICK",
 "job":str(target),"evidence":str(plan)},ensure_ascii=False))
