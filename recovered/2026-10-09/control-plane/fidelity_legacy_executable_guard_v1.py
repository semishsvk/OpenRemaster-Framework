"""Conservative admission safety for ORCH-K003 executable_runtime.
Prevents several known ways to bypass GUI lease by launching a game or global Win32
input script through Python, PowerShell, cmd, node or wscript. This is NOT an
OS-wide execution sandbox and does NOT attest interpreter dependency closure.
"""
from pathlib import Path
import re

INTERPRETERS={"python.exe","pythonw.exe","powershell.exe","pwsh.exe","cmd.exe",
              "wscript.exe","cscript.exe","node.exe"}
DYNAMIC_SWITCHES={"-c","-command","-encodedcommand","-commandwithargs",
                  "-enc","-ec","/c","/k","-m","-encodedarguments"}
GUI_PREFIXES=("dosbox","scummvm","retroarch","godot","game.exe","zorkdos")
GUI_REFS=re.compile(r"(?i)\b(?:dosbox(?:-x)?|scummvm|retroarch|godot|zorkdos(?:\.exe)?)\b")
GLOBAL_CONTROL=re.compile(
 r"(?i)\b(?:SetForegroundWindow|SwitchToThisWindow|BringWindowToTop|"
 r"SetCursorPos|mouse_event|keybd_event|SendInput|GetForegroundWindow|"
 r"FindWindowW?|pyautogui\.(?:click|moveTo|press)|"
 r"win32api\.SetCursorPos|PostThreadMessage|SendMessageW)\b")
PROCESS_SPAWN=re.compile(r"(?i)\b(?:Start-Process|subprocess\.(?:Popen|run)|"
                         r"os\.startfile|CreateProcessW|ShellExecuteW?|WinExec)\b")

ROOT=Path(__file__).resolve().parents[2]
GAME_SOURCE=(ROOT/"source").resolve()

def pe_windows_subsystem(path):
    """Read PE optional header subsystem without running the executable.
    Return 2 for Windows GUI, 3 for console, None for unsupported/unreadable.
    """
    if path.suffix.lower()!=".exe" or not path.is_file():
        return None
    import struct
    try:
        with open(path,"rb") as stream:
            hdr=stream.read(64)
            if len(hdr)<64 or hdr[:2]!=b"MZ":
                return None
            offset=struct.unpack_from("<I",hdr,0x3c)[0]
            if offset>8*1024*1024:
                return None
            stream.seek(offset)
            pe=stream.read(4+20+70)
            if len(pe)<94 or pe[:4]!=b"PE\x00\x00":
                return None
            optional=pe[24:]
            if struct.unpack_from("<H",optional,0)[0] not in (0x10b,0x20b):
                return None
            return struct.unpack_from("<H",optional,68)[0]
    except OSError:
        return None

def _contained(file,root):
    return file==root or root in file.parents

def _return(reason,details):
    return {"schema":"OpenRemaster.LegacyExecutableGuiAdmission.v1",
            "status":"BLOCKED","reason":reason,"details":details}

def check_executable_runtime(execution):
    """Return None for no *statically recognized* GUI bypass, else a rejection.
    A None result is not proof of runtime safety or permission to capture fidelity.
    """
    if not isinstance(execution,dict):
        return _return("EXECUTABLE_RUNTIME_CONTRACT_INVALID",{})
    raw_exe=execution.get("executable")
    args=execution.get("args",[])
    if not isinstance(raw_exe,str) or not raw_exe.strip() or not isinstance(args,list) or not all(isinstance(a,str) for a in args):
        return _return("EXECUTABLE_RUNTIME_ARGUMENTS_INVALID",{})
    exe=Path(raw_exe.strip('"')).resolve()
    exe_name=exe.name.lower()
    if not exe.is_file():
        return _return("EXECUTABLE_RUNTIME_BINARY_UNRESOLVED",{"executable":str(exe)})
    if exe.suffix.lower() in (".bat",".cmd",".ps1",".py",".js",".vbs"):
        return _return("DIRECT_SCRIPT_EXECUTABLE_NOT_ADMITTED",{"executable":str(exe)})
    headless_godot=exe_name.startswith("godot") and "--headless" in args and not execution.get("interactive")
    if pe_windows_subsystem(exe)==2 and not headless_godot:
        return _return("WINDOWS_GUI_PE_SUBSYSTEM_REQUIRES_SUPERVISOR",
                       {"executable":str(exe),"pe_subsystem":2})
    if _contained(exe,GAME_SOURCE) and not headless_godot:
        # Original game corpus is input authority. Direct executable GUI launch
        # belongs to fidelity_runtime or an explicit game adapter, not bare process.
        return _return("SOURCE_EXECUTABLE_REQUIRES_ISOLATED_ADAPTER",
                       {"executable":str(exe)})
    if exe_name.startswith(GUI_PREFIXES) and not headless_godot:
        return _return("KNOWN_GUI_BINARY_REQUIRES_ISOLATED_ADAPTER",
                       {"executable":str(exe)})
    if exe_name not in INTERPRETERS:
        return None
    for i,a in enumerate(args):
        if a.lower() in DYNAMIC_SWITCHES:
            return _return("UNVERIFIED_INTERPRETER_DYNAMIC_COMMAND_BLOCKED",
                           {"switch":a,"executable":str(exe),"arg_index":i})
    if exe_name in {"wscript.exe","cscript.exe"}:
        return _return("UNVERIFIED_SCRIPT_HOST_NOT_ADMITTED",{"executable":str(exe)})
    resolved=[]
    cwd=Path(execution.get("cwd",str(exe.parent))).resolve()
    for i,a in enumerate(args):
        candidate=a.strip().strip('"').strip("'")
        if candidate.startswith("-"):
            continue
        p=Path(candidate)
        if p.suffix.lower() not in (".py",".ps1",".cmd",".bat",".js",".vbs"):
            continue
        full=(p if p.is_absolute() else (cwd/p)).resolve()
        resolved.append((i,full))
    if not resolved:
        return _return("INTERPRETER_SCRIPT_IDENTITY_UNRESOLVED",
                       {"executable":str(exe),"args_count":len(args)})
    if len(resolved)>2:
        return _return("MULTIPLE_SCRIPT_INPUTS_NOT_ATTESTED",{"count":len(resolved)})
    for i,script in resolved:
        if not script.is_file():
            return _return("INTERPRETER_SCRIPT_NOT_FOUND",{"script":str(script)})
        if _contained(script,GAME_SOURCE):
            return _return("SOURCE_SCRIPT_EXECUTION_NOT_ADMITTED",{"script":str(script)})
        if script.stat().st_size>750_000:
            return _return("INTERPRETER_SCRIPT_TOO_LARGE_FOR_STATIC_GUARD",{"script":str(script)})
        source=script.read_text(encoding="utf-8-sig",errors="replace")
        risk=None
        if GLOBAL_CONTROL.search(source):
            risk="GLOBAL_GUI_OR_FOCUS_INPUT"
        elif PROCESS_SPAWN.search(source) and GUI_REFS.search(source):
            risk="PROCESS_LAUNCH_WITH_GAME_GUI_REFERENCE"
        elif script.suffix.lower() in (".vbs",".js"):
            risk="SCRIPT_HOST_DYNAMIC_GUI_UNATTESTED"
        if risk:
            return _return("UNMANAGED_GUI_SCRIPT_REQUIRES_SUPERVISOR",
                           {"script":str(script),"risk_class":risk,"argument_index":i})
    return None
