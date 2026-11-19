"""Original ZORKDOS normal runtime's registered DOSBox-X MCP port: one guest mouse Y move.
No BREAK/RUN, no host input. Experimental external localhost diagnostic sidecar
must not be mistaken for an accepted/reproducible production input trace.
"""
from pathlib import Path
from datetime import datetime,timezone
import socket,json,time
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-live-mousemove-20261009-r4"
out=R/"runtime-test"/"results"/rid
out.mkdir(parents=True,exist_ok=True)
report=out/"MCP-live-guest-movement-trace.json"
if report.exists():raise RuntimeError("MCP_EVENT_REPORT_ALREADY_EXISTS")
port=59093;connected=False;error=None;start=None;rows=[]
def cmd(c,i,x,delay=.18):
 c.sendall((f"REQ {i} {x}\n").encode("ascii"))
 time.sleep(delay)
 reply=c.recv(131072).decode("utf-8",errors="replace")
 success=f"BEGIN {i} OK" in reply and f"END {i}" in reply
 rows.append({"index":i,"command":x,"success":success,
    "response":reply[:1300],
    "seconds_since_connect":round(time.monotonic()-start,4) if start else None})
 if not success:raise RuntimeError("MCP_UNEXPECTED_REPLY:"+x+":"+reply[:300])
 return reply
server=socket.socket()
server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
server.bind(("127.0.0.1",port));server.listen(1);server.settimeout(24)
try:
 c,peer=server.accept()
 if peer[0]!="127.0.0.1":raise RuntimeError("MCP_PEER_NOT_LOCAL")
 connected=True;c.settimeout(5)
 start=time.monotonic()
 cmd(c,1,"PING")
 cmd(c,2,"EXEC OUTD 2A 00")
 cmd(c,3,"EXEC OUTD 28 00000000")
 response=cmd(c,4,"EXEC IND 29")
 if "d05b0740" not in response.lower():
  raise RuntimeError("NO_DOSBOX_X_INTEGRATION_DEVICE")
 planned=40.4
 until=start+planned
 while time.monotonic()<until:time.sleep(min(.3,max(.01,until-time.monotonic())))
 # 0x6F00 in high 16 bits yields (0x6F00/256-1)=+110 relative Y units.
 cmd(c,5,"EXEC OUTD 2A 00")
 cmd(c,6,"EXEC OUTD 28 804200")
 cmd(c,7,"EXEC OUTD 29 6F000A00")
 c.close()
except Exception as e:error=type(e).__name__+":"+str(e)
finally:server.close()
result={
 "schema":"OpenZork.NativeZORKDOSLiveMCPMouseMovementTrace.v1",
 "time_utc":datetime.now(timezone.utc).isoformat(),
 "status":"INTEGRATION_MOUSE_MOVE_ISSUED_WHILE_NATIVE_GAME_RUNNING" if connected and not error else "INPUT_DELIVERY_HOLD",
 "project":"OpenZork","run":rid,"port":port,"connected":connected,
 "integration_identity_verified":any(x["index"]==4 and "d05b0740" in x["response"].lower() for x in rows),
 "command_receipts":rows,"error":error,
 "mouse_delta":{"x":0,"y":110,"units":"emulated mouse relative cursor movement"},
 "mouse_button_events":0,"global_windows_cursor_actions":0,
 "debugger_halted_guest":False,"original_game_input_consumption":"NOT_PROVEN_BY_COMMAND_RECEIPT",
 "production_input_contract":"NOT_ADMITTED_EXTERNAL_SIDECAR",
 "fidelity_verified":False}
report.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],"connected":connected,
 "command_count":len(rows),"event_at":rows[-1]["seconds_since_connect"] if rows else None,
 "error":error,"report":str(report)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
