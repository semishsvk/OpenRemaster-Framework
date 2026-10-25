"""One supervised DOSBox-X INT33 position canary; original game corpus read-only,
private overlay for 20-byte output. NO original ZORKDOS binary runs.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
base=R/"work"/"OpenZork"/"staging"/"dosboxx-int33-absolute-canary-20261009-v9"
exe=base/"guest"/"MSPOSV9.COM"
assert exe.is_file()
emulator=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
rid="openzork-dosboxx-int33-absolute-position-20261009-v9-r1"
conf=base/"MSPOSV9_RUNTIME.conf"
job=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/(rid+".json")
assert not conf.exists() and not job.exists()
corpus=R/"source"/"Zork Nemesis"
content=f"""[dosbox]
machine=svga_s3
memsize=16
captures={{capture_dir}}
[sdl]
fullscreen=false
output=surface
autolock=false
mouse_emulation=always
[render]
frameskip=0
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
mididevice=none
[autoexec]
@echo off
mount C "{corpus}" -ro
mount C "{{private_overlay}}" -t overlay
mount D "{exe.parent}" -ro
C:
D:\\MSPOSV9.COM
pause
"""
conf.write_text(content,encoding="utf-8")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
data={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"ReadOnlyDOSMouseINT33AbsolutePositionPureGuestCanary",
 "inputs":[{"path":str(p),"sha256":sha(p)} for p in (exe,emulator,conf)],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
  "runtime.capture.wgc","runtime.local_capture","runtime.gui_lease.exclusive"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
  "runtime_kind":"dosbox","executable":str(emulator),"config_source":str(conf),
  "args":["-conf","{private_config}","-noconsole"],
  "window_title_contains":"DOSBox-X","capture_backend":"windows_graphics_capture",
  "capture_delay_seconds":3,"require_audio":False,
  "allow_owned_menu_quit":True,"timeout_seconds":26},
 "validation":{"expected_exit_code":0}
}
job.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED_NO_GUEST_PROCESS_STARTED","job":str(job),
 "COM_sha256":sha(exe),"registered_emulator_SHA256":sha(emulator),
 "output":"private overlay/MSPOSV9.BIN",
 "original_game_corpus_read_only":True},ensure_ascii=False))
