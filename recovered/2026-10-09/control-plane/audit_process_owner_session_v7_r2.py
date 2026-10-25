"""Read-only process-wide audit v7 r2, with no regex engine; game GUI + hidden windows.
Known limitations: WMI access/Permission failures are BLOCKED, never interpreted as zero.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import subprocess,json
from fidelity_runtime_isolation_v1 import gui_conflicts,active_console_session,process_identity

R=Path(__file__).resolve().parents[2]
vis=gui_conflicts()
by_pid={}
for w in vis:
 by_pid.setdefault(w["pid"],[]).append({"hwnd":w["hwnd"],"title":w["title"]})

command="""Get-CimInstance Win32_Process |
Where-Object { $_.Name -like 'DOSBox*' -or $_.Name -like 'scummvm*' -or $_.Name -like 'Godot*' -or $_.Name -like 'RetroArch*' } |
Select-Object Name,ProcessId,ParentProcessId,SessionId,CreationDate,ExecutablePath,CommandLine |
ConvertTo-Json -Depth 3 -Compress"""
proc=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",command],
                    capture_output=True,text=True,timeout=40)
if proc.returncode:
 raise RuntimeError("PROCESS_DISCOVERY_FAILED "+proc.stderr[-1200:])
rows=json.loads(proc.stdout) if proc.stdout.strip() else []
if isinstance(rows,dict):rows=[rows]
console=active_console_session()
output=[]
unresolved=[]
for r in rows:
 pid=int(r.get("ProcessId") or 0)
 if pid<1 or int(r.get("SessionId") or -1)!=console:continue
 kind=(r.get("Name") or "").lower()
 argv=r.get("CommandLine") or ""
 # Headless Godot is not competing for the interactive desktop.
 if kind.startswith("godot") and "--headless" in argv.lower():continue
 ident=process_identity(pid)
 if ident is None:
  unresolved.append({"pid":pid,"name":kind,"reason":"PROCESS_IDENTITY_UNREADABLE"})
  continue
 output.append({
  "name":kind,"pid":pid,"session":console,
  "parent_pid":r.get("ParentProcessId"),
  "creation_ticks_100ns":ident["creation_ticks_100ns"],
  "executable":ident["executable"],
  "command_line":argv[:800],
  "visible_windows":by_pid.get(pid,[]),
  "unowned_by_new_supervisor":True,
  "safe_cleanup":"DO_NOT_CLOSE_WITHOUT_ORIGINAL_OWNER_CONTRACT"})
r={
 "schema":"OpenRemaster.ProcessWideGUIContaminationAudit.v2",
 "status":"READ_ONLY_WITH_UNRESOLVED" if unresolved else "READ_ONLY_COMPLETE",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "console_session":console,
 "visible_game_window_count":len(vis),
 "relevant_GUI_PIDs":len(output),
 "hidden_gui_PIDs":sum(not i["visible_windows"] for i in output),
 "by_name":dict(Counter(i["name"] for i in output)),
 "unresolved":unresolved,
 "processes":output,
 "original_game_processes_terminated":0
}
dest=R/"runtime-test"/"results"/"fidelity-process-wide-contamination-audit-v7-r2.json"
if dest.exists():raise RuntimeError("AUDIT_ALREADY_EXISTS")
dest.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":r["status"],"visible_windows":len(vis),
 "relevant_gui_pids":len(output),"hidden_pids":r["hidden_gui_PIDs"],
 "unresolved":len(unresolved),"kinds":r["by_name"],"path":str(dest)},ensure_ascii=False))
