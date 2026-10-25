"""Create unique supervised positive/negative DOSBox-X integration device jobs.
No change to original game source or emulator binaries. Experimental integration
device toggled only in a per-run copied config, and COM fixture mounted read-only.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
folder=R/"work"/"OpenZork"/"staging"/"dosboxx-integration-mouse-20261009-v8-r2"
guest=folder/"guest"/"IGPROBE.COM"
assert guest.is_file()
dosx=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
assert dosx.is_file()
source=R/"source"/"Zork Nemesis"
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
jobs=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"
jobs.mkdir(parents=True,exist_ok=True)
entries=[]
for mode,active in (("enabled",True),("disabled",False)):
 rid="openzork-dosboxx-igmouse-canary-20261009-"+mode
 config=folder/("IGMOUSE_"+mode.upper()+".conf")
 outfile=R/"runtime-test"/"results"/rid
 if config.exists() or (jobs/(rid+".json")).exists() or outfile.exists():
  raise RuntimeError("CANARY_CONFIG_OR_JOB_ALREADY_EXISTS "+mode)
 content=f"""# Only the registered OpenZork DOSBox-X.exe is permitted to execute this job.
# This is a guest mouse I/O device canary, NEVER an original game fidelity replay.
[dosbox]
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
integration device={'true' if active else 'false'}
[mixer]
nosound=true
[midi]
mpu401=none
mididevice=none
[autoexec]
@echo off
mount C "{source}" -ro
mount C "{{private_overlay}}" -t overlay
mount D "{guest.parent}" -ro
C:
D:\\IGPROBE.COM
pause
"""
 config.write_text(content,encoding="utf-8")
 job={
  "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
  "task":"DOSBoxXIntegrationGuestMouseCanary"+mode.title(),
  "inputs":[{"path":str(p),"sha256":h(p)} for p in (guest,config,dosx)],
  "required_capabilities":["runtime.fidelity_isolated",
                           "runtime.passive_capture_diagnostic",
                           "runtime.capture.wgc","runtime.local_capture",
                           "runtime.gui_lease.exclusive"],
  "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
     "runtime_kind":"dosbox","executable":str(dosx),"config_source":str(config),
     "args":["-conf","{private_config}","-noconsole"],
     "window_title_contains":"DOSBox-X","capture_backend":"windows_graphics_capture",
     "capture_delay_seconds":3,"require_audio":False,
     "allow_owned_menu_quit":True,"timeout_seconds":24},
  "validation":{"expected_exit_code":0},
  "acceptance":{"require_validation_pass":True}
 }
 jobfile=jobs/(rid+".json")
 jobfile.write_text(json.dumps(job,indent=2),encoding="utf-8")
 entries.append({"mode":mode,"integration_enabled":active,
                 "config_path":str(config),"config_sha256":h(config),
                 "job_file":str(jobfile),"job_sha256":h(jobfile),
                 "expected_guest_result":"IGMOUSE.BIN in only the own private overlay",
                 "original_game_source_untouched":True})
receipt={"schema":"OpenRemaster.DOSBoxXIntegrationGuestCanaryPlan.v1",
 "status":"STAGED_WITHOUT_RUNNING",
 "original_TGZ_game_read_only":True,
 "test_fixture_sha256":h(guest),
 "exact_emulator_sha256":h(dosx),
 "entries":entries,
 "com_expected_mouse_press":1,"com_expected_release":0,
 "original_game_executed":False,
 "fidelity_verified":False}
outfile=folder/"paired-canary-jobs.json"
outfile.write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":receipt["status"],
 "modes":[{"mode":x["mode"],"job":x["job_file"]} for x in entries],
 "guest_sha256":receipt["test_fixture_sha256"],
 "evidence":str(outfile)},ensure_ascii=False))
