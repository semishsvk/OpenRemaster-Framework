"""Original ZORKDOS normal DOSBox-X run: exact TCP peer PID, process creation,
exe hash + active GUI lease attested before any guest input; one mouse move/click.
Run concurrently with supervised r6 ORCH-K003 job. No global OS input.
External MCP remains DIAGNOSTIC ONLY, never a production fidelity oracle.
"""
from pathlib import Path
from datetime import datetime,timezone
import socket,json,time,hashlib
from fidelity_mcp_peer_attestation_v8 import assert_supervised_mcp_peer
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-extended-newgame-20261009-r6"
run=R/"runtime-test"/"results"/rid
run.mkdir(parents=True,exist_ok=True)
dest=run/"authenticated-MCP-original-native-input-trace.json"
if dest.exists():raise RuntimeError("EXTENDED_INPUT_TRACE_ALREADY_EXISTS")
serverport=59095
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
registered_sha=hashlib.sha256(exe.read_bytes()).hexdigest()
assert registered_sha=="7b549d74523e436d3813d8be1f3347aacb4cbf3ca08af717d3c82a1ab880ecef"
rows=[];binding=None;binding_recheck=None;connected=False;error=None;start=None
def cmd(c,index,text,delay=0.18):
 c.sendall((f"REQ {index} {text}\n").encode("ascii"))
 time.sleep(delay)
 value=c.recv(131072).decode("utf-8",errors="replace")
 success=f"BEGIN {index} OK" in value and f"END {index}" in value
 rows.append({"index":index,"cmd":text,"reply":value[:850],"ok":success,
              "offset_since_connect_s":round(time.monotonic()-start,4)})
 if not success:raise RuntimeError("MCP_COMMAND_NOT_ACCEPTED "+text)
 return value
listener=socket.socket()
listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
listener.bind(("127.0.0.1",serverport))
listener.listen(1);listener.settimeout(26)
try:
 c,peer=listener.accept()
 if peer[0]!="127.0.0.1":raise RuntimeError("MCP_NON_LOOPBACK_PEER")
 connected=True;c.settimeout(6)
 start=time.monotonic()
 cmd(c,1,"PING")
 # Wait until supervisor acquired job object, bound HWND, stored run token.
 owner=run/"fidelity-isolated"/"runtime-identity.json"
 deadline=time.monotonic()+10
 while not owner.is_file() and time.monotonic()<deadline:time.sleep(.1)
 binding=assert_supervised_mcp_peer(
    rid,peer[0],peer[1],serverport,run,registered_sha)
 cmd(c,2,"EXEC OUTD 2A 00")
 cmd(c,3,"EXEC OUTD 28 00000000")
 check=cmd(c,4,"EXEC IND 29")
 if "d05b0740" not in check.lower():raise RuntimeError("MCP_WRONG_GUEST_INTEGRATION_DEVICE")
 intended=start+39.55
 while time.monotonic()<intended:time.sleep(min(.15,max(.01,intended-time.monotonic())))
 # Recheck live owning PID/creation time and same managed lease epoch just before input.
 binding_recheck=assert_supervised_mcp_peer(
    rid,peer[0],peer[1],serverport,run,registered_sha)
 cmd(c,5,"EXEC OUTD 2A 00")
 cmd(c,6,"EXEC OUTD 28 804200")
 cmd(c,7,"EXEC OUTD 29 6F000A00")
 time.sleep(.15)
 cmd(c,8,"EXEC OUTD 2A 00")
 cmd(c,9,"EXEC OUTD 28 804200")
 cmd(c,10,"EXEC OUTD 29 00000880")
 time.sleep(.27)
 cmd(c,11,"EXEC OUTD 2A 00")
 cmd(c,12,"EXEC OUTD 28 804200")
 cmd(c,13,"EXEC OUTD 29 00000800")
 c.close()
except Exception as ex:
 error=type(ex).__name__+":"+str(ex)
finally:
 listener.close()
verified=connected and not error and binding and binding_recheck
result={
 "schema":"OpenZork.AuthenticatedDOSBoxXNewGameDebugAdapterTrace.v1",
 "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"EXACT_SUPERVISED_PID_LEASE_BOUND_INPUT_COMMANDS_ISSUED" if verified else "EXTERNAL_DEBUGGER_BINDING_OR_INPUT_BLOCKED",
 "run_id":rid,"port":serverport,
 "connected":connected,
 "first_peer_attestation":binding,
 "pre_input_peer_attestation":binding_recheck,
 "original_emulator_executable_sha256":registered_sha,
 "events":[{"input":"GUEST_MOUSE_RELATIVE_Y_110","command_id":7},
           {"input":"GUEST_MOUSE_LEFT_DOWN","command_id":10},
           {"input":"GUEST_MOUSE_LEFT_UP","command_id":13}],
 "debugger_command_trace":rows,"error":error,
 "no_global_host_mouse_or_focus":True,
 "original_game_scene_after_click":"NEEDS_LOCAL_CAPTURE_VISUAL_EVIDENCE",
 "original_vs_godot_fidelity":"NOT_VERIFIED",
 "external_sidecar_debugger":"DIAGNOSTIC_ONLY_NOT_INTEGRATED_WORKER"}
dest.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],
 "bound_pid":binding.get("runtime_pid") if binding else None,
 "attested_again_before_input":bool(binding_recheck),
 "events":[{"index":x["index"],"offset":x["offset_since_connect_s"]} for x in rows if x["index"] in (7,10,13)],
 "error":error,"trace":str(dest)},ensure_ascii=False))
raise SystemExit(0 if verified else 1)
