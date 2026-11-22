"""Second debugger canary: double RUN startup plus guest scancode Enter injection.
Actual original game still canonical read-only and GUI fully supervisor-owned.
"""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).parent
old=R/"work"/"OpenZork"/"staging"/"dosboxx-native-mcp-mouse-move-20261009-r1"/"ZORKDOS_DEBUGBOX_NATIVE_MOUSE.conf"
assert old.is_file()
base=R/"work"/"OpenZork"/"staging"/"dosboxx-original-enter-native-20261009-r2"
if base.exists():raise RuntimeError("R2_ALREADY_STAGED")
base.mkdir(parents=True)
text=old.read_text(encoding="utf-8")
assert text.count("mcp_server=59090")==1
assert text.count("autotype -w 8 -p 0.4 enter")==1
text=text.replace("mcp_server=59090","mcp_server=59091")
text=text.replace("autotype -w 8 -p 0.4 enter\n","")
cfg=base/"ZORKDOS_NATIVE_KEYBOARD.conf"
cfg.write_text(text,encoding="utf-8")
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rid="openzork-dosboxx-mcp-native-enter-20261009-r2"
job={
 "schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork",
 "task":"OriginalZORKDOSDebuggerGuestKeyboardEnterIsolationDiagnostic",
 "inputs":[{"path":str(p),"sha256":h(p)} for p in (cfg,exe)],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
    "runtime.capture.wgc","runtime.local_capture","runtime.gui_lease.exclusive"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
    "runtime_kind":"dosbox","executable":str(exe),"config_source":str(cfg),
    "args":["-conf","{private_config}","-noconsole"],
    "window_title_contains":"DOSBox-X","capture_backend":"windows_graphics_capture",
    "capture_schedule_seconds":[8,44],"timeout_seconds":72,
    "require_audio":False,"allow_owned_menu_quit":True},
 "validation":{"expected_exit_code":0}}
jp=R/"runtime-test"/"jobs"/"dosboxx-guest-integration-v8"/(rid+".json")
assert not jp.exists()
jp.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
record={"schema":"OpenZork.DOSBoxXMCPEndToEndKeyboardProbePlan.v1","status":"STAGED",
"run_id":rid,"port":59091,"private_config_sha256":h(cfg),
"original_ZORKDOS_read_only":True,
"input":"ONLY GUEST KEYBOARD SCANCODES THROUGH_DOSBOX_IO: ENTER_PRESS_1C_ENTER_RELEASE_9C",
"breakpoint_activation":"DOUBLE_RUN_PROBE",
"capture_offsets_seconds":[8,44],
"no_windows_global_input":True,
"production_input_contract":"NOT_ADMITTED_DIAGNOSTIC_ONLY",
"job_file":str(jp)}
e=base/"plan.json"
e.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED","port":59091,"job":str(jp),"plan":str(e)}))
