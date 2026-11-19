"""Loopback-only READ access availability test on original ZORKDOS normal launch.
No debugger BREAK/RUN, no emulated keyboard/mouse injection, no host GUI input.
"""
from pathlib import Path
import socket,time,json
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-normalrun-mcp-20261009-r3"
out=R/"runtime-test"/"results"/rid
out.mkdir(parents=True,exist_ok=True)
dest=out/"normal-run-MCP-service-probe.json"
if dest.exists():raise RuntimeError("MCP_AVAILABILITY_RESULT_ALREADY_EXISTS")
port=59092;rows=[];connok=False;error=None
srv=socket.socket()
srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1",port))
srv.listen(1)
srv.settimeout(23)
try:
 c,peer=srv.accept()
 if peer[0]!="127.0.0.1":raise RuntimeError("MCP_UNTRUSTED_PEER")
 connok=True;c.settimeout(6)
 for i,name in enumerate(["PING","EXEC INP 2A","EXEC OUTD 2A 00","EXEC OUTD 28 00000000","EXEC IND 29"],1):
  c.sendall((f"REQ {i} {name}\n").encode("ascii"))
  time.sleep(0.18)
  raw=c.recv(131072).decode(errors="replace")
  rows.append({"command":name,"response":raw[:800],"success":f"BEGIN {i} OK" in raw})
 c.close()
except Exception as e:
 error=type(e).__name__+":"+str(e)
finally:
 srv.close()
state="MCP_CONNECTED_DURING_NORMAL_EXECUTION" if connok and not error and all(x["success"] for x in rows) else "MCP_NORMAL_MODE_UNAVAILABLE_OR_HOLD"
report={
 "schema":"OpenZork.NativeDOSBoxXNormalExecutionMCPAvailability.v1",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":state,"port":port,"loopback_only":True,
 "connected":connok,"commands":rows,"error":error,
 "debugger_break_or_run_command_issued":False,
 "input_to_guest_issued":False,
 "global_host_input_used":False,
 "source_corpus_modified":False,
 "original_fidelity_verified":False}
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":state,"connected":connok,"responses":rows,"error":error,
 "evidence":str(dest)},ensure_ascii=False))
raise SystemExit(0 if connok and not error else 1)
