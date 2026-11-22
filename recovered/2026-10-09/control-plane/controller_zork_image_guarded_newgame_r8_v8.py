"""Experimental original ZORKDOS feedback-gated MCP input.
CLICK MAY ONLY OCCUR if the exact owned local WGC frame positively matches the
original extracted cursor image at the New Game button. No global OS input.
Input is diagnostic-only and cannot issue FIDELITY_PASS.
"""
from pathlib import Path
from datetime import datetime,timezone
import socket,time,json,hashlib
from fidelity_mcp_peer_attestation_v8 import assert_supervised_mcp_peer
from fidelity_local_capture_wgc_v1 import acquire_bound_wgc_frame
from fidelity_original_cursor_gate_v1 import evaluate_original_newgame_cursor

R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"
run=R/"runtime-test"/"results"/rid
run.mkdir(parents=True,exist_ok=True)
out=run/"cursor-guarded-original-newgame-input-trace.json"
if out.exists():raise RuntimeError("CURSOR_GUARDED_TRACE_ALREADY_EXISTS")
port=59097
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
digest=hashlib.sha256(exe.read_bytes()).hexdigest()
assert digest=="7b549d74523e436d3813d8be1f3347aacb4cbf3ca08af717d3c82a1ab880ecef"
rows=[];attestations=[];cursor=None;capture=None;error=None;connected=False;clicked=False;space_sent=False;t0=None

def cmd(sock,index,command,delay=.13):
    sock.sendall((f"REQ {index} {command}\n").encode("ascii"))
    time.sleep(delay)
    reply=sock.recv(131072).decode("utf-8",errors="replace")
    good=f"BEGIN {index} OK" in reply and f"END {index}" in reply
    rows.append({"id":index,"command":command,"OK":good,
      "reply":reply[:700],"at_s":round(time.monotonic()-t0,4)})
    if not good:raise RuntimeError("MCP_COMMAND_FAILED:"+command)
    return reply

def wait_at(t):
    until=t0+t
    while time.monotonic()<until:time.sleep(min(.12,max(.01,until-time.monotonic())))

def owner(peer):
    proof=assert_supervised_mcp_peer(rid,peer[0],peer[1],port,run,digest)
    attestations.append({"at_s":round(time.monotonic()-t0,3),"evidence":proof})
    return proof

srv=socket.socket()
srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1",port));srv.listen(1);srv.settimeout(25)
try:
    client,peer=srv.accept()
    if peer[0]!="127.0.0.1":raise RuntimeError("PEER_IS_NOT_LOOPBACK")
    connected=True;client.settimeout(6);t0=time.monotonic()
    cmd(client,1,"PING")
    identity=run/"fidelity-isolated"/"runtime-identity.json"
    deadline=time.monotonic()+12
    while not identity.is_file() and time.monotonic()<deadline:time.sleep(.1)
    owner(peer)
    cmd(client,2,"EXEC OUTD 2A 00")
    cmd(client,3,"EXEC OUTD 28 00000000")
    assert "d05b0740" in cmd(client,4,"EXEC IND 29").lower()
    wait_at(39.45)
    owner(peer)
    cmd(client,5,"EXEC OUTD 2A 00")
    cmd(client,6,"EXEC OUTD 28 804200")
    cmd(client,7,"EXEC OUTD 29 6F000A00")
    time.sleep(.35)
    # Capture is a sidecar input admission observation, distinct from canonical timeline.
    # Native WGC internally verifies HWND/PID/creation time before and after capture.
    data=json.loads(identity.read_text(encoding="utf-8-sig"))
    if data.get("schema")!="FidelityRuntimeIdentity.v1":
        raise RuntimeError("SUPERVISED_RUNTIME_IDENTITY_MISSING")
    before=run/"fidelity-isolated"/"input-observations"/"pre-click"
    capture=acquire_bound_wgc_frame(before,data["process"],data["window"],data["run_token"])
    cursor=evaluate_original_newgame_cursor(capture["frame_path"])
    if cursor["authorized_single_mouse_click"]:
        owner(peer)
        if time.monotonic()-t0>=54:
            raise RuntimeError("CURSOR_POSITIVE_BUT_CLICK_DEADLINE_EXCEEDED")
        cmd(client,8,"EXEC OUTD 2A 00")
        cmd(client,9,"EXEC OUTD 28 804200")
        cmd(client,10,"EXEC OUTD 29 00000880")
        time.sleep(.27)
        cmd(client,11,"EXEC OUTD 2A 00")
        cmd(client,12,"EXEC OUTD 28 804200")
        cmd(client,13,"EXEC OUTD 29 00000800")
        clicked=True
        wait_at(57.15)
        owner(peer)
        cmd(client,14,"EXEC OUTD 2A 00")
        cmd(client,15,"EXEC OUTD 28 804200")
        cmd(client,16,"EXEC OUTD 29 00000039")
        time.sleep(.24)
        cmd(client,17,"EXEC OUTD 2A 00")
        cmd(client,18,"EXEC OUTD 28 804200")
        cmd(client,19,"EXEC OUTD 29 000000B9")
        space_sent=True
    client.close()
except Exception as exc:
    error=type(exc).__name__+":"+str(exc)
finally:
    srv.close()
status=(
    "BOUND_CURSOR_MATCH_CLICK_AND_MOVIE_SKIP_COMMANDS_SENT"
    if connected and not error and clicked and space_sent else
    "SAFE_NO_CLICK_CURSOR_OUTSIDE_NEWGAME"
    if connected and not error and cursor is not None and not clicked else
    "ORIGINAL_CURSOR_GUARD_OR_MCP_INPUT_HOLD"
)
data={
 "schema":"OpenZork.OriginalNativePreClickWGCGuardedInputTrace.v1",
 "recorded_utc":datetime.now(timezone.utc).isoformat(),
 "status":status,"run_id":rid,
 "peer_attestations":attestations,
 "registered_EXE_sha256":digest,
 "WGC_pre_click_capture":capture,
 "source_cursor_gate":cursor,
 "click_sent":clicked,"space_sent":space_sent,
 "commands":rows,"error":error,
 "original_game_newgame_transition":"NOT_VERIFIED_UNTIL_SEPARATE_TIMELINE",
 "global_keyboard_mouse_events":0,"windows_focus_changes":0,
 "input_adapter_authority":"EXPERIMENTAL_SUPERVISED_DIAGNOSTIC_ONLY",
 "fidelity_verified":False}
out.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":status,"cursor":cursor,
 "click_sent":clicked,"space_sent":space_sent,
 "attestations":len(attestations),"error":error,"evidence":str(out)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
