"""Read-only inventory for pre-existing game GUI processes. Never terminate anything."""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
from fidelity_runtime_isolation_v1 import gui_conflicts

ROOT=Path(__file__).resolve().parents[2]
windows=gui_conflicts()
command=("Get-CimInstance Win32_Process | "
         "Where-Object Name -Match 'dosbox|scummvm|godot|retroarch' | "
         "Select-Object Name,ProcessId,ParentProcessId,SessionId,CreationDate,ExecutablePath,CommandLine | "
         "ConvertTo-Json -Depth 3 -Compress")
query=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],
                     capture_output=True,text=True,timeout=30)
if query.returncode != 0:
    raise RuntimeError(query.stderr[-1000:])
raw=json.loads(query.stdout) if query.stdout.strip() else []
if isinstance(raw,dict):
    raw=[raw]
by_pid={int(p["ProcessId"]):p for p in raw}
rows=[]
for pid in sorted({w["pid"] for w in windows}):
    process=by_pid.get(pid,{})
    ppid=int(process.get("ParentProcessId") or 0)
    parent=by_pid.get(ppid)
    rows.append({
        "pid":pid,"name":process.get("Name"),
        "parent_pid":ppid,"parent_is_running_game_process":bool(parent),
        "session_id":process.get("SessionId"),
        "creation_date":str(process.get("CreationDate")),
        "executable":process.get("ExecutablePath"),
        "command_line":process.get("CommandLine"),
        "windows":[{"hwnd":w["hwnd"],"title":w["title"]} for w in windows if w["pid"]==pid],
        "ownership":"UNKNOWN_LEGACY_PROCESS_NOT_OWNED_BY_NEW_SUPERVISOR",
        "safe_automatic_action":"NONE"
    })
report={
    "schema":"FidelityGUIExistingProcessReconciliation.v1",
    "date_utc":datetime.now(timezone.utc).isoformat(),
    "status":"READ_ONLY_EVIDENCE",
    "runtime_pids":len(rows),"visible_gui_windows":len(windows),
    "policy":"DO_NOT_KILL_UNOWNED_PREEXISTING_PROCESSES",
    "manual_action":"Reconcile each PID against its original project run and checkpoint; stop only after explicit ownership verified",
    "rows":rows
}
out=ROOT/"runtime-test"/"results"/"fidelity-preexisting-gui-reconciliation-20261009.json"
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":report["schema"],"status":report["status"],
                  "runtime_pids":len(rows),"visible_windows":len(windows),
                  "projects_seen":sorted(set((x.get("name") or "") for x in rows)),
                  "output":str(out)},ensure_ascii=False))
