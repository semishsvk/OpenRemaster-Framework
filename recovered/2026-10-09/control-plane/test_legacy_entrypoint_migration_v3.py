"""Verify migrated PowerShell entrypoints never call ScummVM directly.
Tests dry-run and strict busy-desktop rejection only, no game launch.
"""
import json,subprocess,sys
from pathlib import Path
from fidelity_runtime_isolation_v1 import gui_conflicts
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"work"/"OpenZork"/"oracle-runtime"
BACKUP=ROOT/"orchestrator"/"backups"/"openzork-legacy-gui-launchers-20261009-v3"
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
assert before,"Expected GUI occupancy for rejection test"
rows=[]
for name in ("launch-smoke.ps1","record-smoke.ps1"):
 script=BASE/name
 old=BACKUP/name
 assert script.is_file() and old.is_file()
 assert b"Start-Process" in old.read_bytes()
 assert b"Start-Process" not in script.read_bytes()
 assert b"fidelity_legacy_launcher_bridge_v3.py" in script.read_bytes()
 for mode,args in (("dry_run",["-DryRun"]),("strict_blocked",[])):
  p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive",
                    "-ExecutionPolicy","Bypass","-File",str(script),*args],
                   capture_output=True,text=True,timeout=35)
  last=(p.stdout.strip().splitlines() or [""])[-1]
  try:out=json.loads(last)
  except json.JSONDecodeError:out={"parse_error":last}
  expect=(mode=="dry_run" and p.returncode==0 and out.get("status")=="PLAN_ONLY_NO_RUNTIME_LAUNCHED") or (
   mode=="strict_blocked" and p.returncode==2 and out.get("status")=="BLOCKED"
   and out.get("reason")=="FOREIGN_GUI_RUNTIME_PRESENT")
  assert expect,{"script":name,"mode":mode,"returncode":p.returncode,"out":out,"err":p.stderr[-900:]}
  rows.append({"script":name,"case":mode,"status":"PASS","returncode":p.returncode})
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
assert all(after.get(pid)==ticks for pid,ticks in before.items()),"Foreign GUI process closed unexpectedly"
report={"schema":"OpenRemaster.OpenZorkLegacyGUIEntryPointCanary.v3","status":"PASS",
        "cases":rows,"foreign_gui_before":len(before),"foreign_gui_unchanged":len(before),
        "new_game_launches":0}
out=ROOT/"runtime-test"/"results"/"openzork-legacy-entrypoint-canary-v3.json"
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(out))))
