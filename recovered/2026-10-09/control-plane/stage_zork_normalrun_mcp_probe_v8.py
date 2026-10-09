"""Test DOSBox-X MCP accessibility with NORMAL original ZORKDOS, NOT debugbox.
No mouse/keyboard event in this run. Only identify loopback debug service.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).parent
base=R/"work"/"OpenZork"/"staging"/"dosboxx-original-normalrun-mcp-20261009-r3"
if base.exists():raise RuntimeError("NORMALRUN_STAGE_EXISTS")
base.mkdir(parents=True)
source=CP/"examples"/"OpenZork-dosboxx-autotype-oracle-seed.conf"
s=source.read_text(encoding="utf-8")
assert s.count("zorkdos.exe")==1 and s.count("[dosbox]\n")==1 and s.count("[cpu]\n")==1
s=s.replace("[dosbox]\n","[dosbox]\nmcp_server=59092\n",1)
s=s.replace("[cpu]\n","[cpu]\nintegration device=true\n",1)
s=s.replace("[sdl]\n","[sdl]\nmouse_emulation=always\n",1)
cfg=base/"NATIVE_ZORK_WITH_MCP_ATTACHED.conf"
cfg.write_text(s,encoding="utf-8")
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rid="openzork-native-dosboxx-normalrun-mcp-20261009-r3"
job={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"OriginalZorkDOSNormalRuntimeWithReadOnlyMCPServiceProbe",
 "inputs":[{"path":str(p),"sha256":sha(p)} for p in (exe,cfg)],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
  "runtime.capture.wgc","runtime.local_capture","runtime.gui_lease.exclusive"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
    "runtime_kind":"dosbox","executable":str(exe),"config_source":str(cfg),
    "args":["-conf","{private_config}","-noconsole"],
    "window_title_contains":"DOSBox-X","capture_backend":"windows_graphics_capture",
    "capture_schedule_seconds":[10,43],"timeout_seconds":68,
    "require_audio":False,"allow_owned_menu_quit":True},
 "validation":{"expected_exit_code":0}
}
jp=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/(rid+".json")
if jp.exists():raise RuntimeError("NORMALRUN_JOB_EXISTS")
jp.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
plan={"schema":"OpenZork.DOSBoxXMCPNormalExecutionProbe.v1","status":"STAGED",
  "port":59092,"run_id":rid,"game_exec":"zorkdos.exe",
  "debugbox_disabled":True,"autotype_enter":True,
  "integration_device_enabled":True,"private_config_sha256":sha(cfg),
  "original_source_readonly":True,"job":str(jp),
  "all_controls":"LOOPBACK_READ_ONLY_NO_GUEST_INPUT"}
manifest=base/"normal-mcp-plan.json"
manifest.write_text(json.dumps(plan,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED","run_id":rid,"debugbox":False,
 "port":59092,"job":str(jp),"plan":str(manifest)},ensure_ascii=False))
