"""Read-only process-level fidelity contamination audit; includes hidden GUI runtimes.
No process termination, window focus, input, or desktop pixels.
"""
import subprocess,json,os,hashlib
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
from fidelity_runtime_isolation_v1 import gui_conflicts,active_console_session,process_identity
R=Path(__file__).resolve().parents[2]
visible=gui_conflicts()
owners={}
for x in visible:owners.setdefault(x["pid"],[]).append({"hwnd":x["hwnd"],"title":x["title"]})
query="""Get-CimInstance Win32_Process | Where-Object { $_.Name -match '(?i)^(dosbox(?:-x)?|scummvm|godot|retroarch).*\\\\.exe$' } | Select-Object Name,ProcessId,ParentProcessId,SessionId,CreationDate,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3 -Compress"""
# PowerShell source passed in argument vector: no shell parsing/injection of paths or PIDs.
proc=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",query],capture_output=True,text=True,timeout=30)
if proc.returncode:
 raise RuntimeError(proc.stderr[-1000:])
rows=json.loads(proc.stdout) if proc.stdout.strip() else []
if isinstance(rows,dict):rows=[rows]
active=active_console_session()
listed=[]
for item in rows:
 pid=int(item.get("ProcessId") or 0)
 session=int(item.get("SessionId") or -1)
 if pid<1 or session!=active:continue
 name=(item.get("Name") or "").lower()
 args=item.get("CommandLine") or ""
 if name.startswith("godot") and "--headless" in args.lower():continue
 identity=process_identity(pid)
 if identity is None:continue
 if identity["pid"]!=pid:continue
 listed.append({
  "pid":pid,"parent_pid":int(item.get("ParentProcessId") or 0),
  "session_id":session,
  "name":name,"exe":identity["executable"],
  "process_creation_ticks":identity["creation_ticks_100ns"],
  "command":args[:750],
  "visible_windows":owners.get(pid,[]),
  "has_visible_window":bool(owners.get(pid)),
  "ownership":"LEGACY_OR_UNKNOWN_NOT_CURRENT_SUPERVISOR",
  "safe_action":"DO_NOT_TERMINATE_WITHOUT_ORIGINAL_JOB_OWNER_PROOF"
 })
result={
 "schema":"OpenRemaster.ProcessWideOriginalRuntimeContaminationAudit.v1",
 "recorded_at":datetime.now(timezone.utc).isoformat(),
 "status":"READ_ONLY",
 "console_session":active,"all_visible_windows":len(visible),
 "candidate_GUI_process_count":len(listed),
 "candidate_GUI_pids_without_visible_hwnd":sum(not x["has_visible_window"] for x in listed),
 "by_executable":dict(Counter(x["name"] for x in listed)),
 "processes":listed,
 "admission_recommendation":"STRICT_MODE_MUST_EXCLUDE_FOREIGN_GUI_RUNTIME_PROCESSES_NOT_ONLY_VISIBLE_WINDOWS",
 "cleanup_performed":False}
out=R/"runtime-test"/"results"/"fidelity-process-wide-contamination-audit-v7.json"
if out.exists():raise RuntimeError("AUDIT_ALREADY_EXISTS")
out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":result["status"],"visible_windows":len(visible),
 "candidate_pids":len(listed),"hidden_runtime_processes":result["candidate_GUI_pids_without_visible_hwnd"],
 "types":result["by_executable"],"process_summary":[{"pid":x["pid"],"name":x["name"],"has_window":x["has_visible_window"]} for x in listed[:25]],
 "report":str(out)},ensure_ascii=False))
