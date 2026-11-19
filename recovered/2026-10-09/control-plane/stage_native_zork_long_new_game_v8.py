"""Stage unique extended 70 sec original ZORKDOS New Game replay.
Preserve r5 and v1 capture contract, pinned emulator SHA-256, private config/source read-only.
External mouse controller must be confirmed as exact supervised runtime PID + lease.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2]
prior=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/"openzork-native-dosboxx-mcp-new-game-click-20261009-r5.json"
base_cfg=R/"work"/"OpenZork"/"staging"/"dosboxx-original-native-newgame-click-20261009-r5"/"ZORKDOS_NATIVE_MOUSE_CLICK.conf"
assert prior.is_file() and base_cfg.is_file()
rid="openzork-native-dosboxx-extended-newgame-20261009-r6"
stage=R/"work"/"OpenZork"/"staging"/"dosboxx-extended-newgame-20261009-r6"
if stage.exists():raise RuntimeError("R6_STAGE_ALREADY_EXISTS")
stage.mkdir(parents=True)
config=stage/"NATIVE_ZORK_EXTENDED_NEWGAME.conf"
text=base_cfg.read_text(encoding="utf-8")
assert text.count("mcp_server=59094")==1
config.write_text(text.replace("mcp_server=59094","mcp_server=59095"),encoding="utf-8")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
job=json.loads(prior.read_text(encoding="utf-8"))
job["job_id"]=rid
job["task"]="NativeOriginalZORKDOSNewGameExtended70SecAuthenticatedMouseReplay"
job["execution"]["config_source"]=str(config)
job["execution"]["capture_schedule_contract"]="v2_extended"
job["execution"]["capture_schedule_seconds"]=[35,42,55,70]
job["execution"]["timeout_seconds"]=100
job["inputs"][0]={"path":str(config),"sha256":sha(config)}
path=prior.with_name(rid+".json")
if path.exists():raise RuntimeError("R6_JOB_EXISTS_NO_OVERWRITE")
path.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
data={"schema":"OpenZork.OriginalNativeNewGameExtendedReplayPlan.v1",
"status":"STAGED_ONLY_NO_LAUNCH","run_id":rid,
"capture_contract":"OpenRemaster.BoundedFrameSchedule.v2",
"capture_offsets_s":[35,42,55,70],
"original_source_read_only":True,
"exe_sha256":job["inputs"][1]["sha256"],
"mcp_listening_port":59095,
"additional_control":"MCP_TCP_SOCKET_PID_CREATION_EXE_HASH_LEASE_ATTESTATION",
"original_game_fidelity":"NOT_VERIFIED",
"previous_control":"openzork-native-dosboxx-live-mousemove-20261009-r4",
"first_native_click":"openzork-native-dosboxx-mcp-new-game-click-20261009-r5",
"job":str(path)}
doc=stage/"staged-replay-plan.json"
doc.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":data["status"],"run_id":rid,"times":data["capture_offsets_s"],
"job":str(path),"plan":str(doc)},ensure_ascii=False))
