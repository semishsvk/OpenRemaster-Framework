"""Stage a single-use DOSBox-X loopback MCP debugger transport canary (READ + RUN).
Debugger control is not fidelity and is not allowed to interact with other OS processes.
"""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).parent
base=R/"work"/"OpenZork"/"staging"/"dosboxx-integration-mouse-20261009-v8-r2"
guest=base/"guest"/"IGPROBE.COM"
assert guest.is_file()
rid="openzork-dosboxx-debug-mcp-io-probe-20261009-r1"
port=59089
run=R/"runtime-test"/"results"/rid
conf=base/"DOSBOXX_MCP_IO_PROBE.conf"
jobfile=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/(rid+".json")
if conf.exists() or jobfile.exists() or run.exists():
 raise RuntimeError("MCP_CANARY_ALREADY_STAGED")
dosx=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
config=f"""[dosbox]
machine=svga_s3
memsize=16
mcp_server={port}
captures={{capture_dir}}
[sdl]
fullscreen=false
output=surface
autolock=false
mouse_emulation=always
[render]
aspect=false
scaler=none
[cpu]
core=normal
cputype=pentium
cycles=max
integration device=true
[mixer]
nosound=true
[midi]
mpu401=none
[autoexec]
@echo off
mount C "F:\\Remaster Framework\\source\\Zork Nemesis" -ro
mount C "{{private_overlay}}" -t overlay
mount D "{guest.parent}" -ro
C:
debugbox D:\\IGPROBE.COM
pause
"""
conf.write_text(config,encoding="utf-8")
job={"schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"DOSBoxXNativeDebuggerMCP_IOReadOnlyTransportProbe",
 "inputs":[{"path":str(p),"sha256":h(p)} for p in (guest,conf,dosx)],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
  "runtime.capture.wgc","runtime.local_capture","runtime.gui_lease.exclusive"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
  "runtime_kind":"dosbox","executable":str(dosx),"config_source":str(conf),
  "args":["-conf","{private_config}","-noconsole"],"window_title_contains":"DOSBox-X",
  "capture_backend":"windows_graphics_capture","capture_delay_seconds":6,
  "require_audio":False,"allow_owned_menu_quit":True,"timeout_seconds":28},
 "validation":{"expected_exit_code":0}}
jobfile.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
out=base/"mcp-probe-transport-plan.json"
out.write_text(json.dumps({"schema":"OpenRemaster.DOSBoxXMCPLoopbackProbePlan.v1",
 "status":"STAGED_ONLY","run_id":rid,"mcp_port":port,
 "private_config_sha256":h(conf),
 "guest_fixture_sha256":h(guest),
 "debug_command":"debugbox D:\\IGPROBE.COM",
 "source_read_only":True,"test_does_not_launch_original_Zork":True,
 "listener_transport":"127.0.0.1_SINGLE_CONNECTION",
 "job":str(jobfile)},indent=2),encoding="utf-8")
print(json.dumps({"status":"STAGED_ONLY","port":port,"job":str(jobfile),
 "evidence":str(out)},ensure_ascii=False))
