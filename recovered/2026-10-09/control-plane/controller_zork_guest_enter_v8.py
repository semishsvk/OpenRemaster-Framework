"""Original ZORKDOS guest keyboard Enter from isolated DOSBox-X MCP integration ports.
This is an out-of-band, loopback-only debugger EXPERIMENT; not a production
validator and not evidence that a frame/state is faithful until externally checked.
"""
from pathlib import Path
from datetime import datetime,timezone
import socket,time,json
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-dosboxx-mcp-native-enter-20261009-r2"
run.mkdir(parents=True,exist_ok=True)
out=run/"guest-enter-MCP-trace.json"
if out.exists():raise RuntimeError("GUEST_ENTER_MCP_TRACE_EXISTS")
port=59091
rows=[];error=None;connected=False;origin=None
def cmd(conn,num,name,delay=0.15):
 conn.sendall(f"REQ {num} {name}\n".encode("ascii"))
 time.sleep(delay)
 reply=conn.recv(131072).decode("utf-8",errors="replace")
 good=f"BEGIN {num} OK" in reply and f"END {num}" in reply
 rows.append({"id":num,"command":name,"reply":reply[:900],
              "offset_s":round(time.monotonic()-origin,3) if origin else None,
              "OK":good})
 if not good:raise RuntimeError("MCP_COMMAND_FAILED:"+name+":"+reply[:300])
 return reply
sock=socket.socket()
sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
sock.bind(("127.0.0.1",port))
sock.listen(1);sock.settimeout(25)
try:
 conn,peer=sock.accept()
 if peer[0]!="127.0.0.1":raise RuntimeError("UNTRUSTED_PEER")
 connected=True
 conn.settimeout(6)
 cmd(conn,1,"PING")
 cmd(conn,2,"EXEC OUTD 2A 00")
 cmd(conn,3,"EXEC OUTD 28 00000000")
 ident=cmd(conn,4,"EXEC IND 29")
 if "d05b0740" not in ident.lower():raise RuntimeError("INTEGRATION_DEVICE_ID_INVALID")
 cmd(conn,5,"EXEC RUN",.35)
 cmd(conn,6,"EXEC RUN",.35)
 origin=time.monotonic()
 until=origin+10.0
 while time.monotonic()<until:time.sleep(min(.2,max(.01,until-time.monotonic())))
 cmd(conn,7,"BREAK")
 cmd(conn,8,"EXEC EV CS EIP AX BX CX DX")
 # Integration register is 0x804200. Subcommand 00 adds raw PS/2 scan byte.
 # 0x1C enter make, 0x9C enter break. One press while guest runs before release.
 cmd(conn,9,"EXEC OUTD 2A 00")
 cmd(conn,10,"EXEC OUTD 28 804200")
 cmd(conn,11,"EXEC OUTD 29 0000001C")
 cmd(conn,12,"EXEC RUN",.4)
 cmd(conn,13,"BREAK")
 cmd(conn,14,"EXEC OUTD 2A 00")
 cmd(conn,15,"EXEC OUTD 28 804200")
 cmd(conn,16,"EXEC OUTD 29 0000009C")
 cmd(conn,17,"EXEC RUN")
 conn.close()
except Exception as e:
 error=type(e).__name__+":"+str(e)
finally:
 sock.close()
result={
 "schema":"OpenZork.GuestDOSKeyboardDebuggerEnterTrace.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":"ENTER_SCAN_INJECTED_VIA_GUEST_EMULATOR_NOT_GAMEPLAY_PROOF" if connected and not error else "GUEST_ENTER_INJECTION_HOLD",
 "run_id":run.name,
 "loopback_port":port,"connected":connected,
 "dosbox_integration_ID_verified":any(r["id"]==4 and "d05b0740" in r["reply"].lower() for r in rows),
 "keyboard_press_scancode":"1C","keyboard_release_scancode":"9C",
 "global_host_keyboard_used":False,"host_mouse_changed":False,"focus_changes":False,
 "debugger_command_trace":rows,"error":error,
 "original_game_input_consumed":"NOT_PROVEN",
 "fidelity_verified":False}
out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],"events":[(r["id"],r["command"],r["offset_s"]) for r in rows],
 "error":error,"trace":str(out)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
