"""One original DOSBox-X guest menu click plus guest Spacebar during original FMV.
Independent TCP-client PID, process creation, EXE SHA and supervisor GUI lease attested
before BOTH input phases. Runs only on localhost, and never moves host OS cursor/focus.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,socket,time,hashlib
from fidelity_mcp_peer_attestation_v8 import assert_supervised_mcp_peer
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-newgame-skipintro-20261009-r7"
run=R/"runtime-test"/"results"/rid
run.mkdir(parents=True,exist_ok=True)
path=run/"authenticated-guest-newgame-spacebar-trace.json"
if path.exists():raise RuntimeError("R7_INPUT_TRACE_ALREADY_EXISTS_NO_OVERWRITE")
port=59096
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
digest=hashlib.sha256(exe.read_bytes()).hexdigest()
assert digest=="7b549d74523e436d3813d8be1f3347aacb4cbf3ca08af717d3c82a1ab880ecef"
att=[];events=[];error=None;connected=False;t0=None
def command(conn,index,text,delay=.16):
    conn.sendall(f"REQ {index} {text}\n".encode("ascii"))
    time.sleep(delay)
    reply=conn.recv(131072).decode("utf-8",errors="replace")
    ok=(f"BEGIN {index} OK" in reply and f"END {index}" in reply)
    events.append({"id":index,"cmd":text,"OK":ok,"reply":reply[:850],
       "offset_since_connection_s":round(time.monotonic()-t0,4)})
    if not ok:raise RuntimeError("MCP_COMMAND_REJECTED:"+text+":"+reply[:140])
    return reply
def attest(peer):
    verified=assert_supervised_mcp_peer(
        rid,peer[0],peer[1],port,run,digest)
    att.append({"offset_since_connection_s":round(time.monotonic()-t0,4),
                "binding":verified})
    return verified
def wait_until(seconds):
    until=t0+seconds
    while time.monotonic()<until:time.sleep(min(.14,max(.01,until-time.monotonic())))
listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
listener.bind(("127.0.0.1",port));listener.listen(1);listener.settimeout(25)
try:
    conn,peer=listener.accept()
    if peer[0]!="127.0.0.1":raise RuntimeError("FOREIGN_MCP_CONNECTION")
    conn.settimeout(5);connected=True;t0=time.monotonic()
    command(conn,1,"PING")
    owner=run/"fidelity-isolated"/"runtime-identity.json"
    deadline=time.monotonic()+12
    while not owner.exists() and time.monotonic()<deadline:time.sleep(.1)
    attest(peer)
    command(conn,2,"EXEC OUTD 2A 00")
    command(conn,3,"EXEC OUTD 28 00000000")
    magic=command(conn,4,"EXEC IND 29")
    if "d05b0740" not in magic.lower():
        raise RuntimeError("INTEGRATION_DEVICE_IDENTITY_MISMATCH")
    wait_until(39.45)
    attest(peer)
    command(conn,5,"EXEC OUTD 2A 00")
    command(conn,6,"EXEC OUTD 28 804200")
    command(conn,7,"EXEC OUTD 29 6F000A00")
    time.sleep(.14)
    command(conn,8,"EXEC OUTD 2A 00")
    command(conn,9,"EXEC OUTD 28 804200")
    command(conn,10,"EXEC OUTD 29 00000880")
    time.sleep(.28)
    command(conn,11,"EXEC OUTD 2A 00")
    command(conn,12,"EXEC OUTD 28 804200")
    command(conn,13,"EXEC OUTD 29 00000800")
    wait_until(57.15)
    attest(peer)
    # DOSBox-X device register 0x804200, keyboard raw set-1 scan code.
    # Space MAKE 0x39, BREAK 0xB9; from original Zork manual skip FMVs.
    command(conn,14,"EXEC OUTD 2A 00")
    command(conn,15,"EXEC OUTD 28 804200")
    command(conn,16,"EXEC OUTD 29 00000039")
    time.sleep(.24)
    command(conn,17,"EXEC OUTD 2A 00")
    command(conn,18,"EXEC OUTD 28 804200")
    command(conn,19,"EXEC OUTD 29 000000B9")
    conn.close()
except Exception as ex:
    error=type(ex).__name__+":"+str(ex)
finally:
    listener.close()
passed=bool(connected and not error and len(att)==3)
report={
 "schema":"OpenZork.AuthenticatedNativeGameMenuAndFMVSkipTrace.v1",
 "status":"EXACT_PROCESS_BOUND_MENU_CLICK_AND_GUEST_SPACE_DELIVERED_GAME_STATE_PENDING" if passed else "INPUT_PROCESS_BINDING_OR_DELIVERY_HOLD",
 "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
 "run_id":rid,"loopback_port":port,"connected":connected,"runtime_exe_sha256":digest,
 "supervised_peer_attestations":att,
 "independent_pre_click_and_pre_space_binding":len(att)==3,
 "input_sequence":[
   {"event":"guest_mouse_y_plus_110","request":7},
   {"event":"guest_mouse_button_down","request":10},
   {"event":"guest_mouse_button_up","request":13},
   {"event":"guest_space_make","request":16},
   {"event":"guest_space_break","request":19}
 ],
 "MCP_commands":events,"error":error,
 "zero_host_mouse_keyboard_events":True,"global_focus_unmodified":True,
 "original_Zork_video_skip":"UNVERIFIED_PENDING_FRAME_EVIDENCE",
 "original_gameplay_state":"NOT_VERIFIED",
 "input_adapter":"EXPERIMENTAL_EXTERNAL_LOOPBACK_DIAGNOSTIC_ONLY",
 "fidelity_verified":False}
path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"attestations":len(att),
"bound_pid":att[0]["binding"]["runtime_pid"] if att else None,
"input_event_actual_offsets":[{"id":e["id"],"t":e["offset_since_connection_s"]} for e in events if e["id"] in (7,10,13,16,19)],
"error":error,"evidence":str(path)},ensure_ascii=False))
raise SystemExit(0 if passed else 1)
