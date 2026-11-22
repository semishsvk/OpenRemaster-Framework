"""One native mouse-movement diagnostic in normal ZORKDOS, no DEBUGBOX.
Only loopback port changes; read-only game source, owned process/win handles.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
base=R/"work"/"OpenZork"/"staging"/"dosboxx-original-normalrun-mcp-20261009-r3"
old=base/"NATIVE_ZORK_WITH_MCP_ATTACHED.conf"
rid="openzork-native-dosboxx-live-mousemove-20261009-r4"
newdir=R/"work"/"OpenZork"/"staging"/"dosboxx-original-normalrun-mousemove-20261009-r4"
if newdir.exists():raise RuntimeError("LIVE_MOUSE_MOVE_STAGE_EXISTS")
newdir.mkdir(parents=True)
data=old.read_text(encoding="utf-8")
assert data.count("mcp_server=59092")==1
config=newdir/"ZORK_NATIVE_LIVE_MOUSEMOVE.conf"
config.write_text(data.replace("mcp_server=59092","mcp_server=59093"),encoding="utf-8")
prior=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/"openzork-native-dosboxx-normalrun-mcp-20261009-r3.json"
job=json.loads(prior.read_text(encoding="utf-8"))
job["job_id"]=rid
job["task"]="NativeZORKDOSLiveMCPMouseMovementNoGlobalInput"
exe=job["execution"]
exe["config_source"]=str(config)
exe["capture_schedule_seconds"]=[39,44]
job["inputs"]=[{"path":str(config),"sha256":hashlib.sha256(config.read_bytes()).hexdigest()},job["inputs"][0]]
jf=prior.with_name(rid+".json")
assert not jf.exists()
jf.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
proof={"schema":"OpenZork.NativeMCPMouseMoveExperiment.v1","status":"STAGED",
"port":59093,"game":"ZORKDOS.EXE_NORMAL_RUN_NO_DEBUGBOX","private_config_sha256":hashlib.sha256(config.read_bytes()).hexdigest(),
"original_game_source_readonly":True,
"event":"EMULATOR_INTEGRATION_MOUSE_MOVE_Y_PLUS_110_AT_APPROX_40S",
"windows_host_pointer_input":False,"debugger_BREAK_RUN":False,
"capture_schedule":[39,44],"fidelity":"NOT_ELIGIBLE",
"job":str(jf)}
ref=newdir/"plan.json"
ref.write_text(json.dumps(proof,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED","port":59093,"job":str(jf),"evidence":str(ref)}))
