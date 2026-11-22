"""Single-use localhost MCP debugger transport probe; only read device identification.
No mouse press, no game input, no host-global cursor, no user desktop focus.
Caller starts this listener BEFORE supervised DOSBox-X job.
"""
from pathlib import Path
import socket,time,json,hashlib
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2]
run=R/"runtime-test"/"results"/"openzork-dosboxx-debug-mcp-io-probe-20261009-r1"
report=run/"local-mcp-transport-audit.json"
run.mkdir(exist_ok=True,parents=True)
if report.exists():raise RuntimeError("MCP_TRANSPORT_AUDIT_EXISTS")
port=59089
commands=[
 "PING",
 "CAPABILITIES",
 "EXEC INP 2A",
 "EXEC OUTD 2A 00",
 "EXEC OUTD 28 00000000",
 "EXEC IND 29",
 "EXEC RUN"
]
results=[]
listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
listener.bind(("127.0.0.1",port));listener.listen(1)
listener.settimeout(35)
connected=False;address=None;error=None
try:
 conn,address=listener.accept()
 connected=address[0]=="127.0.0.1"
 conn.settimeout(4)
 for i,cmd in enumerate(commands,1):
  full=(f"REQ {i} "+cmd+"\n").encode("ascii")
  conn.sendall(full)
  time.sleep(0.25)
  try:
   received=conn.recv(131072).decode("utf-8",errors="replace")
  except Exception as e:
   received="ERR:"+type(e).__name__+":"+str(e)
  results.append({"command":cmd,"reply":received[:2200]})
 conn.close()
except Exception as e:
 error=type(e).__name__+":"+str(e)
finally:
 listener.close()
data={
 "schema":"OpenRemaster.DOSBoxXMCP_IOTransportProbe.v1",
 "recorded_utc":datetime.now(timezone.utc).isoformat(),
 "status":"MCP_CONNECTED_READ_COMMANDS_ISSUED" if connected and not error else "MCP_TRANSPORT_HOLD",
 "loopback_only":True,"connected":connected,"peer_address":address,
 "port":port,"commands":results,"error":error,
 "keyboard_mouse_events_sent":False,
 "original_ZORKDOS_not_executed":True,"fidelity_promotion":False}
report.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":data["status"],"connected":connected,
 "commands":[{"cmd":x["command"],"reply":x["reply"][:340]} for x in results],
 "error":error,"evidence":str(report)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
