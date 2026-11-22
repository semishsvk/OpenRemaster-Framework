"""Positive and negative strict GUI admission rows, including hidden-window case.
Read-only live WMI snapshot, no GUI runtime launched or terminated.
"""
import json
from pathlib import Path
from unittest.mock import patch
from fidelity_process_wide_preflight_v7 import (
 filter_console_gui_rows,console_runtime_process_conflicts
)
from fidelity_runtime_isolation_v1 import IsolationError,gui_conflicts,active_console_session

session=active_console_session()
rows=[
 {"ProcessId":111,"SessionId":session,"Name":"DOSBox.exe","CommandLine":"DOSBox -conf private.conf","ParentProcessId":2},
 {"ProcessId":112,"SessionId":session,"Name":"Godot.exe","CommandLine":"Godot.exe --headless --path C:\\run","ParentProcessId":2},
 {"ProcessId":113,"SessionId":session+1,"Name":"scummvm.exe","CommandLine":"scummvm.exe znemesis","ParentProcessId":2},
 {"ProcessId":114,"SessionId":session,"Name":"notepad.exe","CommandLine":"notepad.exe","ParentProcessId":2},
 {"ProcessId":115,"SessionId":session,"Name":"DOSBox-X.exe","CommandLine":"dosbox-x.exe -conf game.conf","ParentProcessId":2}
]
chosen=filter_console_gui_rows(rows,session)
assert {x["pid"] for x in chosen}=={111,115},chosen
excluded=filter_console_gui_rows(rows,session,exclude_pids=(115,))
assert len(excluded)==1 and excluded[0]["pid"]==111
with patch("fidelity_process_wide_preflight_v7.subprocess.run") as mocked:
 mocked.return_value.returncode=5
 mocked.return_value.stderr="ACCESS_DENIED"
 try:
  console_runtime_process_conflicts()
 except IsolationError as e:
  assert e.reason=="PROCESS_WIDE_PREFLIGHT_QUERY_FAILED",e.reason
 else:raise AssertionError("PROCESS_QUERY_FAILURE_NOT_BLOCKED")
live=console_runtime_process_conflicts()
vis=gui_conflicts()
assert isinstance(live,list)
assert len(live)>0,"Live audit unexpectedly sees zero game GUI processes"
assert all(r.get("pid")>0 and r.get("creation_ticks_100ns")>0 for r in live)
report={
 "schema":"OpenRemaster.ProcessWideStrictGUIAdmissionCanary.v1",
 "status":"PASS",
 "fixture_hidden_DOSBoxX_correctly_detected":True,
 "fixture_headless_Godot_excluded":True,
 "fixture_other_windows_session_excluded":True,
 "fixture_non_game_executable_excluded":True,
 "query_failure_fail_closed":True,
 "live_gui_runtime_pid_count":len(live),
 "live_visible_game_window_count":len(vis),
 "process_kills":0,
 "fidelity_test_acceptance":"NOT_PERFORMED"}
R=Path(__file__).resolve().parents[2]
target=R/"runtime-test"/"results"/"fidelity-process-wide-guard-canary-v7.json"
if not target.exists():target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
else:
 old=json.loads(target.read_text(encoding="utf-8-sig"))
 # Repeating this canary should not overwrite original time-dependent snapshot.
 assert old["status"]=="PASS"
print(json.dumps({"status":"PASS","fixture_GUI_pids":[x["pid"] for x in chosen],
 "live_pids":len(live),"WMI_fail_closed":True,"evidence":str(target)}))
