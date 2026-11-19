"""Original ZORKDOS.EXE read-only guest mouse movement diagnostic over DOSBox-X debugger MCP.
EXPERIMENTAL external loopback controller; no host-global mouse/focus or fidelity claim.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
stage=R/"work"/"OpenZork"/"staging"/"dosboxx-native-mcp-mouse-move-20261009-r1"
if stage.exists():raise RuntimeError("MCP_NATIVE_MOVE_STAGE_ALREADY_EXISTS")
stage.mkdir(parents=True)
source=CP/"examples"/"OpenZork-dosboxx-autotype-oracle-seed.conf"
text=source.read_text(encoding="utf-8")
assert text.count("zorkdos.exe")==1
assert text.count("[dosbox]")==1
assert text.count("[cpu]")==1
text=text.replace("zorkdos.exe","debugbox ZORKDOS.EXE")
text=text.replace("[dosbox]\n","[dosbox]\nmcp_server=59090\n",1)
text=text.replace("[cpu]\n","[cpu]\nintegration device=true\n",1)
text=text.replace("[sdl]\n","[sdl]\nmouse_emulation=always\n",1)
config=stage/"ZORKDOS_DEBUGBOX_NATIVE_MOUSE.conf"
config.write_text(text,encoding="utf-8")
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
hash=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rid="openzork-original-dosboxx-native-mcp-mousemove-20261009-r1"
job={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"EXP_SOURCE_BACKED_DOSBOXX_DEBUGGER_MOUSE_MOVE_NOT_FIDELITY",
 "inputs":[{"path":str(p),"sha256":hash(p)} for p in (config,exe)],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
                          "runtime.capture.wgc","runtime.local_capture",
                          "runtime.gui_lease.exclusive"],
 "execution":{
  "kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
  "runtime_kind":"dosbox","executable":str(exe),
  "config_source":str(config),
  "args":["-conf","{private_config}","-noconsole"],
  "window_title_contains":"DOSBox-X",
  "capture_backend":"windows_graphics_capture",
  "capture_schedule_seconds":[37,44],"timeout_seconds":72,
  "require_audio":False,"allow_owned_menu_quit":True
 },
 "validation":{"expected_exit_code":0}
}
file=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/(rid+".json")
assert not file.exists()
file.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
rec={
 "schema":"OpenZork.DOSBoxXMCPGuestMovePlan.v1",
 "status":"STAGED_ONLY",
 "run_id":rid,"private_config":str(config),
 "private_config_sha256":hash(config),
 "emulator_exe_sha256":hash(exe),
 "debugger_local_port":59090,
 "debugger_guest_command":"debugbox ZORKDOS.EXE",
 "mouse_diagnostic_event":"EMULATED_RELATIVE_Y_MOVE_120_BY_OUTD_28_29",
 "no_host_global_mouse_or_focus":True,
 "out_of_band_debugger_sidecar":"DIAGNOSTIC_ONLY_NOT_PRODUCTION_INPUT_CONTRACT",
 "expected_screenshots_at_offsets":[37,44],
 "save_original_game_source_read_only":True,
 "fidelity_verified":False}
path=stage/"planned-debugger-movement.json"
path.write_text(json.dumps(rec,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":rec["status"],"job":str(file),
 "config":str(config),"port":59090,"evidence":str(path)},ensure_ascii=False))
