"""Non-mutating owner/process snapshot; does not close any windows."""
import json,sys,os,subprocess,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fidelity_runtime_isolation_v1 import gui_conflicts,process_identity,active_console_session,process_session
R=Path(__file__).resolve().parents[2]; C=Path(__file__).resolve().parent
w=gui_conflicts(); ids={}
for x in w:
 pid=x["pid"]
 if pid not in ids:ids[pid]=process_identity(pid)
cmd=("Get-CimInstance Win32_Process | Where-Object Name -Match '^(DOSBox|Godot|scummvm|retroarch)' | "
     "Select-Object Name,ProcessId,ParentProcessId,CreationDate,SessionId,ExecutablePath,CommandLine | ConvertTo-Json -Depth 2 -Compress")
p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,timeout=30)
procs=json.loads(p.stdout) if p.stdout.strip() else []
if isinstance(procs,dict):procs=[procs]
runs=[]
for item in sorted((R/"orchestrator"/"native-worker"/"queue"/"running").glob("*.json")):
 try:
  j=json.loads(item.read_text())
  runs.append({"job_id":j.get("job_id"),"project":j.get("project"),"task":j.get("task"),"path":str(item),"execution":j.get("execution",{}).get("kind")})
 except Exception as e:runs.append({"path":str(item),"error":str(e)})
out={"schema":"OpenRemaster.GUIViewOwnershipAudit.v3","date_utc":datetime.now(timezone.utc).isoformat(),
"status":"READ_ONLY",
"active_session":active_console_session(),"worker_session":process_session(os.getpid()),
"windows":w,"owner_identity":ids,"processes":procs,"native_worker_running_jobs":runs}
dest=R/"runtime-test"/"results"/"fidelity-gui-current-owner-audit-v3.json"
dest.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"READ_ONLY","visible_windows":len(w),"unique_pids":len(ids),
  "names":{name:sum(name.lower() in Path(x["executable"]).name.lower() for x in w) for name in ("DOSBox","ScummVM","Godot")},
  "native_running_jobs":runs,
  "process_summaries":[{"pid":x.get("ProcessId"),"session":x.get("SessionId"),"exe":x.get("Name"),
   "args":(x.get("CommandLine") or "")[:185]} for x in procs if x.get("ProcessId") in ids],
  "report":str(dest)},ensure_ascii=False))
