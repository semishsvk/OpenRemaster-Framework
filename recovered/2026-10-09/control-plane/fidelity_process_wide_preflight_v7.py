"""Fail-closed strict GUI preflight for hidden/minimized game runtime processes.
Exact active Windows console session only; excludes correctly marked Godot --headless.
Never terminates, activates, screenshares or changes an existing process.
"""
from pathlib import Path
import subprocess,json
from fidelity_runtime_isolation_v1 import IsolationError,active_console_session,process_identity

CIM_QUERY="""Get-CimInstance Win32_Process |
Where-Object { $_.Name -like 'DOSBox*' -or $_.Name -like 'scummvm*' -or $_.Name -like 'Godot*' -or $_.Name -like 'RetroArch*' } |
Select-Object Name,ProcessId,ParentProcessId,SessionId,ExecutablePath,CommandLine |
ConvertTo-Json -Depth 3 -Compress"""

def filter_console_gui_rows(rows,session,exclude_pids=()):
    if not isinstance(rows,list):raise IsolationError("PROCESS_WIDE_PREFLIGHT_FORMAT_INVALID")
    out=[]
    excluded={int(x) for x in exclude_pids}
    for row in rows:
        if not isinstance(row,dict):
            raise IsolationError("PROCESS_WIDE_PREFLIGHT_ROW_INVALID")
        try:pid=int(row.get("ProcessId") or 0);sid=int(row.get("SessionId") or -1)
        except (ValueError,TypeError):
            raise IsolationError("PROCESS_WIDE_PREFLIGHT_ID_INVALID")
        if not pid or pid in excluded or sid!=session:
            continue
        name=(row.get("Name") or "").lower()
        args=(row.get("CommandLine") or "").lower()
        if name.startswith("godot") and "--headless" in args:
            continue
        if not name.startswith(("dosbox","scummvm","godot","retroarch")):
            continue
        out.append({"pid":pid,"name":name,"command":row.get("CommandLine") or "",
                    "session":sid,"parent_pid":row.get("ParentProcessId")})
    return out

def console_runtime_process_conflicts(exclude_pids=()):
    try:
        p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",CIM_QUERY],
            capture_output=True,text=True,timeout=30)
    except (subprocess.TimeoutExpired,OSError) as e:
        raise IsolationError("PROCESS_WIDE_PREFLIGHT_QUERY_UNAVAILABLE",
                             {"error":type(e).__name__})
    if p.returncode!=0:
        raise IsolationError("PROCESS_WIDE_PREFLIGHT_QUERY_FAILED",
                             {"returncode":p.returncode,"stderr_tail":p.stderr[-400:]})
    try:
        rows=json.loads(p.stdout) if p.stdout.strip() else []
    except json.JSONDecodeError:
        raise IsolationError("PROCESS_WIDE_PREFLIGHT_NOT_JSON")
    if isinstance(rows,dict):rows=[rows]
    found=filter_console_gui_rows(rows,active_console_session(),exclude_pids)
    trusted=[]
    for r in found:
        ident=process_identity(r["pid"])
        if ident is None:
            raise IsolationError("PROCESS_WIDE_PREFLIGHT_PID_OWNER_UNREADABLE",
                                 {"pid":r["pid"]})
        trusted.append(dict(r,
            executable=ident["executable"],
            creation_ticks_100ns=ident["creation_ticks_100ns"]))
    return trusted
