"""Single native DOSBox-X guest mouse move + one left click at original New Game button.
On a loopback-only MCP connection to a registered, supervised ZORKDOS DOSBox-X.
Does not control Windows pointer, focus, or shared desktop; status diagnostic-only.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,socket,time
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-mcp-new-game-click-20261009-r5"
out=R/"runtime-test"/"results"/rid
out.mkdir(parents=True,exist_ok=True)
trace=out/"MCP-newgame-original-native-input-trace.json"
if trace.exists():raise RuntimeError("MCP_NEWGAME_TRACE_ALREADY_EXISTS")
port=59094
connected=False;error=None;t0=None;rows=[]
def command(sock,index,name,delay=0.18):
 sock.sendall((f"REQ {index} {name}\n").encode("ascii"))
 time.sleep(delay)
 response=sock.recv(131072).decode("utf-8",errors="replace")
 ok=f"BEGIN {index} OK" in response and f"END {index}" in response
 rows.append({"id":index,"command":name,"OK":ok,
  "offset_since_connect_seconds":round(time.monotonic()-t0,4),
  "response":response[:900]})
 if not ok:raise RuntimeError("MCP_EVENT_REJECTED:"+name+":"+response[:150])
 return response
server=socket.socket()
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind(("127.0.0.1",port));server.listen(1);server.settimeout(25)
try:
 c,peer=server.accept()
 if peer[0]!="127.0.0.1":raise RuntimeError("MCP_NOT_LOOPBACK")
 connected=True;t0=time.monotonic()
 c.settimeout(5)
 command(c,1,"PING")
 command(c,2,"EXEC OUTD 2A 00")
 command(c,3,"EXEC OUTD 28 00000000")
 identity=command(c,4,"EXEC IND 29")
 if "d05b0740" not in identity.lower():
  raise RuntimeError("WRONG_INTEGRATION_DEVICE")
 intended=t0+40.25
 while time.monotonic()<intended:
  time.sleep(min(.25,max(.01,intended-time.monotonic())))
 # Source-backed integration: 0x804200 subcode 0x0A +110 guest cursor Y
 command(c,5,"EXEC OUTD 2A 00")
 command(c,6,"EXEC OUTD 28 804200")
 command(c,7,"EXEC OUTD 29 6F000A00")
 time.sleep(.20)
 # subcode 0x08 mouse left down: data low 0x80, subcode byte 0x08.
 command(c,8,"EXEC OUTD 2A 00")
 command(c,9,"EXEC OUTD 28 804200")
 command(c,10,"EXEC OUTD 29 00000880")
 time.sleep(.36)
 # release: data 0x00000800.
 command(c,11,"EXEC OUTD 2A 00")
 command(c,12,"EXEC OUTD 28 804200")
 command(c,13,"EXEC OUTD 29 00000800")
 c.close()
except Exception as e:
 error=type(e).__name__+":"+str(e)
finally:
 server.close()
state="NATIVE_DOS_MOUSE_MOVE_CLICK_INJECTED_GAME_STATE_UNVERIFIED" if connected and not error else "NATIVE_DOS_MOUSE_CLICK_DELIVERY_HOLD"
record={
 "schema":"OpenZork.DOSBoxXOriginalNativeNewGameMouseEventTrace.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":state,"run_id":rid,"connected":connected,
 "debugger_loopback_only":True,"port":port,
 "device_identity_confirmed":any(x["id"]==4 and "d05b0740" in x["response"].lower() for x in rows),
 "original_game":"ZORKDOS.EXE","emulator":"DOSBOX_X_2026_10_01",
 "inputs":[{"event":"emulated_cursor_y_plus_110","id":7},
           {"event":"emulated_left_button_press","id":10},
           {"event":"emulated_left_button_release","id":13}],
 "global_mouse_events":0,"global_key_events":0,
 "windows_focus_changes":0,"debugger_breakpoints_used":False,
 "native_guest_game_NewGame_activated":"NOT_YET_VERIFIED_BY_STATE",
 "production_fidelity_input_adapter":"UNVALIDATED_EXTERNAL_LOOPBACK_SIDECAR",
 "trace":rows,"error":error,
 "fidelity_verified":False}
trace.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":state,"commands":len(rows),
 "event_schedule_actual":[{"name":x["command"],"at":x["offset_since_connect_seconds"]} for x in rows if x["id"] in (7,10,13)],
 "error":error,"trace":str(trace)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
