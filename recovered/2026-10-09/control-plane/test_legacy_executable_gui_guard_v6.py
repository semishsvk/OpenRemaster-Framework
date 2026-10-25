"""Static and ORCH-K003 end-to-end fail-closed checks of old global mouse/focus launchers.
Never execute a dangerous script or GUI binary. Read-only evidence except canary receipts.
"""
import json,subprocess,sys,uuid
from pathlib import Path
from fidelity_legacy_executable_guard_v1 import check_executable_runtime,pe_windows_subsystem

ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
PYTHON=ROOT/"orchestrator"/"native-worker"/"runtime"/"python.exe"
assert PYTHON.is_file()
old_focus=ROOT/"work"/"OpenZork"/"tools"/"oracle_restore_activate.py"
old_dosbox=ROOT/"work"/"OpenZork"/"tools"/"dosbox_internal_capture.py"
safe=CP/"test_leases.py"
fixture=ROOT/"work"/"OpenRemaster"/"fidelity_fixture"/"synthetic_scummvm_oracle.exe"
godot=ROOT/"source"/"Godot"/"Godot_v4.7.2-stable_win64.exe"
assert all(x.is_file() for x in (old_focus,old_dosbox,safe,fixture,godot))
assert pe_windows_subsystem(fixture)==2,pe_windows_subsystem(fixture)
assert pe_windows_subsystem(PYTHON)==3,pe_windows_subsystem(PYTHON)
checks=[]
def banned(label,exe,args,expected):
 r=check_executable_runtime({"executable":str(exe),"args":args})
 assert r is not None and r["reason"]==expected,(label,r)
 checks.append({"name":label,"status":"BLOCKED","reason":expected})
banned("legacy_global_focus_cursor",PYTHON,["-B",str(old_focus)],
       "UNMANAGED_GUI_SCRIPT_REQUIRES_SUPERVISOR")
banned("legacy_dosbox_keyboard",PYTHON,["-B",str(old_dosbox)],
       "UNMANAGED_GUI_SCRIPT_REQUIRES_SUPERVISOR")
banned("python_dynamic_code",PYTHON,["-c","print('hello')"],
       "UNVERIFIED_INTERPRETER_DYNAMIC_COMMAND_BLOCKED")
banned("native_unknown_win32_gui_fixture",fixture,[],
       "WINDOWS_GUI_PE_SUBSYSTEM_REQUIRES_SUPERVISOR")
banned("original_game_godot_direct_gui",godot,["--path",str(ROOT/"work"/"OpenZork"/"runtime")],
       "WINDOWS_GUI_PE_SUBSYSTEM_REQUIRES_SUPERVISOR")
assert check_executable_runtime({"executable":str(PYTHON),"args":["-B",str(safe)]}) is None
checks.append({"name":"known_safe_headless_python_test","status":"NO_STATIC_BLOCK"})
assert check_executable_runtime({"executable":str(godot),"args":["--headless","--path",str(ROOT/"work"/"OpenZork"/"runtime")]}) is None
checks.append({"name":"explicit_godot_headless","status":"NO_STATIC_BLOCK"})
id="gui-script-bypass-negative-"+uuid.uuid4().hex[:9]
job={"schema":"ORCH-K003.Job.v1","job_id":id,"project":"OpenZork",
     "task":"LegacyGuiBypassAdmissionCanary","inputs":[],"required_capabilities":[],
     "execution":{"kind":"executable_runtime","executable":str(PYTHON),
                  "args":["-B",str(old_focus)]},
     "validation":{"expected_exit_code":0}}
jp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(id+".json")
jp.parent.mkdir(parents=True,exist_ok=True)
jp.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
p=subprocess.run([str(PYTHON),"-B",str(CP/"orch_k003.py"),str(jp)],
                 capture_output=True,text=True,timeout=18)
out=ROOT/"runtime-test"/"results"/id
receipt=json.loads((out/"control-receipt.json").read_text(encoding="utf-8"))
assert p.returncode==2 and receipt["status"]=="BLOCKED" and receipt["reason"]=="UNMANAGED_GUI_SCRIPT_REQUIRES_SUPERVISOR",(p.returncode,receipt)
assert not (out/"result.json").exists() and not (out/"fidelity-isolated").exists()
result={"schema":"OpenRemaster.LegacyGuiExecutableAdmissionCanary.v1",
        "status":"PASS","cases":checks,
        "tested_ORCH_K003_receipt":str(out/"control-receipt.json"),
        "blocked_legacy_script":str(old_focus),
        "gui_exe_pe_subsystem":pe_windows_subsystem(fixture),
        "headless_python_pe_subsystem":pe_windows_subsystem(PYTHON),
        "dangerous_scripts_executed":0,"gui_processes_launched":0}
target=ROOT/"runtime-test"/"results"/"legacy-gui-executable-admission-canary-v6.json"
target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"PASS","checks":len(checks),"gui_pe_subsystem":pe_windows_subsystem(fixture),
"ORCH_BLOCKED":receipt["reason"],"unsafe_scripts_launched":0,"report":str(target)},ensure_ascii=False))
