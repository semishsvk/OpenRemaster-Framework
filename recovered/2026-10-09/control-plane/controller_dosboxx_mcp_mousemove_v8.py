"""One-shot localhost MCP session / guest injected mouse movement in ORIGINAL ZORKDOS.
External DEBUGGER sidecar is not yet a production input contract: NO fidelity promotion.
Only privately configured DOSBox-X job on port 59090, no global host mouse/keyboard.
"""
from pathlib import Path
from datetime import datetime,timezone
import socket,time,json,hashlib
R=Path(__file__).resolve().parents[2]
rid="openzork-original-dosboxx-native-mcp-mousemove-20261009-r1"
base=R/"runtime-test"/"results"/rid
base.mkdir(exist_ok=True,parents=True)
target=base/"debugger-mousemove-trace.json"
if target.exists():raise RuntimeError("DEBUGGER_TRACE_ALREADY_EXISTS")
port=59090
rows=[];connected=False;error=None;started=None
server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind(("127.0.0.1",port))
server.listen(1);server.settimeout(25)
def send(conn,index,command,wait=0.2):
    request=f"REQ {index} {command}\n"
    conn.sendall(request.encode("ascii"))
    time.sleep(wait)
    try:reply=conn.recv(131072).decode(errors="replace")
    except Exception as exc:raise RuntimeError("MCP_REPLY_TIMEOUT "+str(exc))
    ok=f"BEGIN {index} OK" in reply and f"END {index}" in reply
    rows.append({"id":index,"command":command,"response":reply[:2300],"ok":ok,
                 "event_wallclock_utc":datetime.now(timezone.utc).isoformat(),
                 "since_run_seconds":round(time.monotonic()-started,3) if started else None})
    if not ok:raise RuntimeError("MCP_COMMAND_FAILED:"+command+":"+reply[:250])
    return reply
try:
    conn,peer=server.accept()
    connected=peer[0]=="127.0.0.1"
    if not connected:raise RuntimeError("MCP_PEER_NOT_LOOPBACK")
    conn.settimeout(5)
    send(conn,1,"PING")
    send(conn,2,"EXEC OUTD 2A 00")
    send(conn,3,"EXEC OUTD 28 00000000")
    ident=send(conn,4,"EXEC IND 29")
    if "d05b0740" not in ident.lower():
        raise RuntimeError("MCP_INTEGRATION_IDENTITY_NOT_VERIFIED:"+ident)
    send(conn,5,"EXEC RUN")
    started=time.monotonic()
    # Allow the first title/menu to settle. No host OS keys, no window focus.
    intended=39.7
    while time.monotonic()-started<intended:
        time.sleep(min(.25,max(.01,intended-(time.monotonic()-started))))
    send(conn,6,"BREAK")
    send(conn,7,"EXEC EV CS EIP AX BX CX DX")
    # DOSBox-X integration register 0x804200, Y movement subcommand 0x0A:
    # upper 16-bit 0x7900 => (0x7900/256 - 1) = +120 relative mouse units.
    send(conn,8,"EXEC OUTD 2A 00")
    send(conn,9,"EXEC OUTD 28 804200")
    send(conn,10,"EXEC OUTD 29 79000A00")
    send(conn,11,"EXEC RUN")
    conn.close()
except Exception as exc:
    error=type(exc).__name__+":"+str(exc)
finally:
    server.close()
proof={
 "schema":"OpenZork.DOSBoxXOriginalNativeMouseMoveDebuggerTrace.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":"MCP_INTERNAL_MOUSE_MOVE_ISSUED_NO_GAME_CONSUMPTION_PROOF" if connected and not error else "MCP_DIAGNOSTIC_HOLD",
 "run_id":rid,"connected":connected,"peer_loopback_only":True,
 "configured_mcp_port":port,"authenticated_process_binding":"LOCAL_PORT_AND_SUPERVISED_CONFIG_ONLY_NOT_PID_ATTESTED",
 "integration_identification_verified":any(x["id"]==4 and "d05b0740" in x["response"].lower() for x in rows),
 "mouse_event":"MOUSE_CURSOR_MOVED_DELTA_Y_PLUS_120_IN_EMULATOR",
 "global_cursor_moves":0,"global_keyboard_input":0,"focus_changes":0,
 "emulator_owner_cleanup":"ORCH_K003_OWNED_JOB_OBJECT",
 "control_trace":rows,
 "error":error,
 "original_game_consumption":"NOT_VERIFIED_YET",
 "independent_reconstruction_fidelity":"NOT_VERIFIED"}
target.write_text(json.dumps(proof,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":proof["status"],"connection":connected,
 "commands":[{"id":x["id"],"name":x["command"],"ok":x["ok"],"at":x["since_run_seconds"]} for x in rows],
 "error":error,"trace":str(target)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
