"""Original ZORKDOS feedback-calibrated guest mouse, experimental adapter.
Exact localhost peer PID/creation/EXE SHA and GUI lease authenticated. All mouse
movement is emulator-native and every calibration WGC image bound to that HWND.
Click only if independently extracted original cursor is verified on New Game.
No host cursor/keyboard/focus mutation. Never awards fidelity.
"""
from pathlib import Path
from datetime import datetime,timezone
import socket,time,json,hashlib
from fidelity_mcp_peer_attestation_v8 import assert_supervised_mcp_peer
from fidelity_local_capture_wgc_v1 import acquire_bound_wgc_frame
from fidelity_native_cursor_feedback_v1 import (
 detect_extracted_cursor_position,safe_positive_feedback_delta,guest_port_motion_value)
R=Path(__file__).resolve().parents[2]
rid="openzork-native-dosboxx-cursor-feedback-newgame-20261009-r10"
run=R/"runtime-test"/"results"/rid
run.mkdir(parents=True,exist_ok=True)
dest=run/"feedback-guest-mouse-trace.json"
if dest.exists():raise RuntimeError("R9_GUEST_MOUSE_TRACE_EXISTS")
port=59099
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
digest=hashlib.sha256(exe.read_bytes()).hexdigest()
assert digest=="7b549d74523e436d3813d8be1f3347aacb4cbf3ca08af717d3c82a1ab880ecef"
events=[];att=[];observations=[];error=None;t0=None;connected=False;clicked=False;space=False
last_state=None

def command(sock,index,name,delay=.12):
 sock.sendall((f"REQ {index} {name}\n").encode("ascii"))
 time.sleep(delay)
 reply=sock.recv(131072).decode("utf-8",errors="replace")
 ok=f"BEGIN {index} OK" in reply and f"END {index}" in reply
 events.append({"id":index,"command":name,"OK":ok,"reply":reply[:800],
                "seconds":round(time.monotonic()-t0,4)})
 if not ok:raise RuntimeError("EMULATOR_COMMAND_NOT_ACCEPTED:"+name)
 return reply

def attest(peer):
 proof=assert_supervised_mcp_peer(rid,peer[0],peer[1],port,run,digest)
 att.append({"seconds":round(time.monotonic()-t0,3),"result":proof})
 return proof

def wait_at(second):
 until=t0+second
 while time.monotonic()<until:time.sleep(min(.12,max(.01,until-time.monotonic())))

srv=socket.socket()
srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
srv.bind(("127.0.0.1",port));srv.listen(1);srv.settimeout(25)
try:
 client,peer=srv.accept()
 if peer[0]!="127.0.0.1":raise RuntimeError("MCP_UNTRUSTED_NON_LOOPBACK")
 client.settimeout(6);connected=True;t0=time.monotonic()
 seq=0
 def send(name,delay=.12):
  global seq
  seq+=1
  return command(client,seq,name,delay)
 send("PING")
 identity=run/"fidelity-isolated"/"runtime-identity.json"
 deadline=time.monotonic()+13
 while not identity.is_file() and time.monotonic()<deadline:time.sleep(.1)
 attest(peer)
 send("EXEC OUTD 2A 00")
 send("EXEC OUTD 28 00000000")
 if "d05b0740" not in send("EXEC IND 29").lower():
  raise RuntimeError("NO_REGISTERED_GUEST_MOUSE_DEVICE")
 wait_at(39.40)
 attest(peer)
 send("EXEC OUTD 2A 00")
 send("EXEC OUTD 28 804200")
 send("EXEC OUTD 29 6F000A00")
 time.sleep(.25)
 bundle=json.loads(identity.read_text(encoding="utf-8-sig"))
 assert bundle["schema"]=="FidelityRuntimeIdentity.v1"
 for attempt in range(5):
  path=run/"fidelity-isolated"/"input-observations"/("calibration-%02d"%(attempt+1))
  cap=acquire_bound_wgc_frame(path,bundle["process"],bundle["window"],bundle["run_token"])
  observed=detect_extracted_cursor_position(cap["frame_path"])
  observation={"attempt":attempt+1,"at_seconds":round(time.monotonic()-t0,3),
               "frame_sha256":cap["frame_sha256"],
               "native_WGC_attestation_sha256":cap["manifest_sha256"],
               "cursor":observed}
  observations.append(observation)
  last_state=observed
  if observed["NewGame_click_allowed"]:
   attest(peer)
   if time.monotonic()-t0>=54:
    raise RuntimeError("POSITIVE_CURSOR_BUT_TIMING_WINDOW_EXPIRED")
   send("EXEC OUTD 2A 00")
   send("EXEC OUTD 28 804200")
   send("EXEC OUTD 29 00000880")
   time.sleep(.27)
   send("EXEC OUTD 2A 00")
   send("EXEC OUTD 28 804200")
   send("EXEC OUTD 29 00000800")
   clicked=True
   break
  if attempt==4:break
  move=safe_positive_feedback_delta(observed)
  observation["bounded_positive_guest_motion"]=move
  if move["status"]!="GUEST_POSITIVE_MOVE_ONLY":
   raise RuntimeError("UNEXPECTED_GUEST_MOTION_STATE")
  for axis in ("x","y"):
   amount=move[axis+"_delta"]
   if amount:
    send("EXEC OUTD 2A 00")
    send("EXEC OUTD 28 804200")
    send("EXEC OUTD 29 "+guest_port_motion_value(axis,amount))
  time.sleep(.26)
 if clicked:
  wait_at(57.15)
  attest(peer)
  send("EXEC OUTD 2A 00")
  send("EXEC OUTD 28 804200")
  send("EXEC OUTD 29 00000039")
  time.sleep(.24)
  send("EXEC OUTD 2A 00")
  send("EXEC OUTD 28 804200")
  send("EXEC OUTD 29 000000B9")
  space=True
 client.close()
except Exception as e:
 error=type(e).__name__+":"+str(e)
finally:
 srv.close()
status=("FEEDBACK_CALIBRATED_NEWGAME_CLICK_AND_MOVIE_SKIP_SENT" if clicked and space and not error else
        "FEEDBACK_GUARD_BLOCKED_CLICK_NO_MOVIE_SKIP" if connected and not error else
        "FEEDBACK_INPUT_BINDING_OR_CALIBRATION_ERROR")
report={
 "schema":"OpenZork.NativeGuestCursorFeedbackAndMovieSkipTrace.v1",
 "recorded_utc":datetime.now(timezone.utc).isoformat(),
 "status":status,"run_id":rid,"registered_emulator_exe_sha256":digest,
 "supervised_peer_binding":att,
 "cursor_feedback_observations":observations,
 "final_source_cursor_status":last_state,
 "button_press_released":clicked,
 "movie_skip_space_sent":space,
 "loopback_control_trace":events,
 "error":error,"global_host_cursor_or_focus_actions":0,
 "guest_input_adapter":"EXPERIMENTAL_FEEDBACK_LOWER_TRUST_THAN_FIDELITY",
 "original_gameplay_scene_verification":"NOT_YET",
 "fidelity_verified":False}
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":status,"observations":[{"try":x["attempt"],
"cursor":x["cursor"]["status"],"xy":[x["cursor"]["x"],x["cursor"]["y"]],
"move":x.get("bounded_positive_guest_motion")} for x in observations],
"clicked":clicked,"space":space,"error":error,
"bound_owner":att[0]["result"]["runtime_pid"] if att else None,"evidence":str(dest)},ensure_ascii=False))
raise SystemExit(0 if connected and not error else 1)
