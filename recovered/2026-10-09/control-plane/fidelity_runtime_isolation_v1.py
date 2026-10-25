"""HomePC interactive fidelity resource guard, Win32-only, fail closed.
Original source trees are never modified. This module does not capture RDC video.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

SCHEMA = "FidelityRuntimeIsolation.v1"
MUTEX_NAME = r"Global\OpenRemaster_HomePC_InteractiveFidelity_v1"
GAME_GUI_NAMES = ("dosbox", "scummvm", "godot", "retroarch", "dosbox-x")
K = ctypes.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None
U = ctypes.WinDLL("user32", use_last_error=True) if os.name == "nt" else None
WAIT_OBJECT_0, WAIT_ABANDONED, WAIT_TIMEOUT = 0, 0x80, 0x102
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def atomic_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    t = p.with_name(p.name + "." + str(os.getpid()) + ".tmp")
    t.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(t, p)

class IsolationError(Exception):
    def __init__(self, reason, details=None):
        super().__init__(reason)
        self.reason, self.details = reason, details or {}

class InteractiveMutex:
    def __init__(self, name=MUTEX_NAME):
        self.name = name
        self.handle = None
        self.abandoned = False
    def acquire(self):
        if os.name != "nt":
            raise IsolationError("WINDOWS_RUNTIME_REQUIRED")
        K.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        K.CreateMutexW.restype = wintypes.HANDLE
        K.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        K.WaitForSingleObject.restype = wintypes.DWORD
        self.handle = K.CreateMutexW(None, False, self.name)
        if not self.handle:
            raise IsolationError("MUTEX_CREATE_FAILED", {"winerror": ctypes.get_last_error()})
        outcome = K.WaitForSingleObject(self.handle, 0)
        if outcome not in (WAIT_OBJECT_0, WAIT_ABANDONED):
            self.close(release=False)
            if outcome == WAIT_TIMEOUT:
                raise IsolationError("GUI_LEASE_BUSY")
            raise IsolationError("GUI_MUTEX_WAIT_FAILED", {"result": int(outcome)})
        self.abandoned = outcome == WAIT_ABANDONED
        return self
    def close(self, release=True):
        if self.handle:
            if release:
                K.ReleaseMutex.argtypes = (wintypes.HANDLE,)
                K.ReleaseMutex(self.handle)
            K.CloseHandle.argtypes = (wintypes.HANDLE,)
            K.CloseHandle(self.handle)
            self.handle = None
    def __enter__(self):
        return self.acquire()
    def __exit__(self, typ, value, trace):
        self.close()

def active_console_session():
    if os.name != "nt":
        raise IsolationError("WINDOWS_RUNTIME_REQUIRED")
    K.WTSGetActiveConsoleSessionId.restype = wintypes.DWORD
    active = int(K.WTSGetActiveConsoleSessionId())
    if active == 0xFFFFFFFF:
        raise IsolationError("ACTIVE_INTERACTIVE_SESSION_MISSING")
    return active

def process_session(pid):
    if os.name != "nt":
        raise IsolationError("WINDOWS_RUNTIME_REQUIRED")
    sid = wintypes.DWORD()
    K.ProcessIdToSessionId.argtypes = (wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    if not K.ProcessIdToSessionId(int(pid), ctypes.byref(sid)):
        raise IsolationError("PROCESS_SESSION_QUERY_FAILED")
    return int(sid.value)

def _process_handle(pid):
    K.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    K.OpenProcess.restype = wintypes.HANDLE
    return K.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))

def process_identity(pid):
    if os.name != "nt":
        raise IsolationError("WINDOWS_RUNTIME_REQUIRED")
    handle = _process_handle(pid)
    if not handle:
        return None
    try:
        n = wintypes.DWORD(32768)
        b = ctypes.create_unicode_buffer(n.value)
        K.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        K.QueryFullProcessImageNameW.restype = wintypes.BOOL
        if not K.QueryFullProcessImageNameW(handle, 0, b, ctypes.byref(n)):
            return None
        create = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        K.GetProcessTimes.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME))
        if not K.GetProcessTimes(handle, ctypes.byref(create), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        ticks = (int(create.dwHighDateTime) << 32) | int(create.dwLowDateTime)
        return {"pid": int(pid), "executable": b.value, "creation_ticks_100ns": ticks}
    finally:
        K.CloseHandle(handle)

def desktop_windows():
    if os.name != "nt":
        raise IsolationError("WINDOWS_RUNTIME_REQUIRED")
    windows = []
    CALLBACK = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    U.IsWindowVisible.argtypes = (wintypes.HWND,)
    U.IsWindowVisible.restype = wintypes.BOOL
    U.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    U.GetWindowThreadProcessId.restype = wintypes.DWORD
    U.GetWindowTextLengthW.argtypes = (wintypes.HWND,)
    U.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    def visit(hwnd, param):
        if not U.IsWindowVisible(hwnd):
            return True
        n = U.GetWindowTextLengthW(hwnd)
        s = ctypes.create_unicode_buffer(max(1, n + 1))
        U.GetWindowTextW(hwnd, s, n + 1)
        pid = wintypes.DWORD()
        U.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append({"hwnd": int(hwnd), "pid": int(pid.value), "title": s.value})
        return True
    U.EnumWindows.argtypes = (CALLBACK, wintypes.LPARAM)
    U.EnumWindows.restype = wintypes.BOOL
    cb = CALLBACK(visit)
    if not U.EnumWindows(cb, 0):
        raise IsolationError("WINDOW_ENUMERATION_FAILED", {"winerror": ctypes.get_last_error()})
    return windows

def gui_conflicts(exclude_pids=()):
    conflicts = []
    cache = {}
    skip = set(map(int, exclude_pids))
    for w in desktop_windows():
        if w["pid"] in skip:
            continue
        pid = w["pid"]
        if pid not in cache:
            cache[pid] = process_identity(pid)
        ident = cache[pid]
        if ident is None:
            # Unknown owner: cannot promote this window into any identity proof.
            continue
        name = Path(ident["executable"]).name.lower()
        if any(x in name for x in GAME_GUI_NAMES):
            conflicts.append(dict(w, executable=ident["executable"], creation_ticks_100ns=ident["creation_ticks_100ns"]))
    return conflicts

def bind_window(pid, creation_ticks, exe, title_filter=None):
    identity = process_identity(pid)
    if not identity or identity["creation_ticks_100ns"] != creation_ticks or os.path.normcase(identity["executable"]) != os.path.normcase(str(exe)):
        raise IsolationError("PROCESS_IDENTITY_CHANGED")
    matches = [w for w in desktop_windows() if w["pid"] == int(pid)]
    if title_filter:
        matches = [w for w in matches if title_filter.lower() in w["title"].lower()]
    if not matches:
        raise IsolationError("OWNED_WINDOW_NOT_FOUND")
    if len(matches) != 1:
        raise IsolationError("OWNED_WINDOW_AMBIGUOUS", {"matches": matches})
    return matches[0]

def assert_window_owned(hwnd, pid, creation_ticks, executable):
    """Validate an exact HWND without relying on title or activation order."""
    identity=process_identity(pid)
    if not identity or identity["creation_ticks_100ns"]!=creation_ticks:
        raise IsolationError("PROCESS_IDENTITY_CHANGED")
    if os.path.normcase(identity["executable"])!=os.path.normcase(str(executable)):
        raise IsolationError("PROCESS_EXECUTABLE_CHANGED")
    matches=[w for w in desktop_windows() if w["hwnd"]==int(hwnd)]
    if len(matches)!=1 or matches[0]["pid"]!=int(pid):
        raise IsolationError("HWND_NOT_OWNED_BY_PROCESS")
    return matches[0]

def validate_private_runtime_config(kind, args, config_path, saves_dir, source_root):
    """Require explicit private config and save routing; no writable mount of canonical source."""
    a = [str(x).lower() for x in args]
    c = str(config_path).lower()
    s = str(saves_dir).lower()
    if kind == "dosbox":
        if "-conf" not in a or a.index("-conf") + 1 >= len(a) or a[a.index("-conf") + 1] != c:
            raise IsolationError("DOSBOX_PRIVATE_CONFIG_REQUIRED")
        if "-c" in a:
            raise IsolationError("UNVALIDATED_DOSBOX_INLINE_COMMAND")
        text = Path(config_path).read_text(encoding="utf-8-sig", errors="replace")
        run_dir = Path(config_path).resolve().parent.parent
        for raw in text.splitlines():
            line = raw.split("#",1)[0].split(";",1)[0].strip()
            if not line:
                continue
            if re.match(r"(?i)^captures\s*=",line):
                capture_setting=line.split("=",1)[1].strip().strip('"')
                cpath=Path(capture_setting)
                resolved_capture=(cpath if cpath.is_absolute() else run_dir/cpath).resolve()
                if resolved_capture!=run_dir and run_dir not in resolved_capture.parents:
                    raise IsolationError("DOSBOX_CAPTURE_OUTSIDE_PRIVATE_RUN",{"line":line})
            if re.match(r"(?i)^imgmount\s+",line):
                if not re.search(r"(?i)(?:^|\s)-t\s+(?:iso|cdrom)(?:\s|$)",line):
                    raise IsolationError("DOSBOX_WRITABLE_IMAGE_MOUNT_UNVERIFIED",{"line":line})
            if not re.match(r"(?i)^mount\s+",line):
                continue
            m = re.match(r"(?i)^mount\s+[a-z]\s+(?:\"([^\"]+)\"|'([^']+)'|(\S+))", line)
            if not m:
                raise IsolationError("DOSBOX_MOUNT_UNPARSEABLE",{"line":line})
            target = Path(next(part for part in m.groups() if part)).expanduser()
            writable = not bool(re.search(r"(?i)(?:^|\s)-ro(?:\s|$)",line))
            if not writable or not target.is_absolute():
                continue
            resolved = target.resolve()
            source = Path(source_root).resolve()
            if resolved == source or resolved in source.parents or source in resolved.parents:
                raise IsolationError("SOURCE_MOUNT_NOT_READ_ONLY",{"line":line})
            if resolved != run_dir and run_dir not in resolved.parents:
                raise IsolationError("DOSBOX_WRITABLE_MOUNT_OUTSIDE_PRIVATE_RUN",{"line":line})
    elif kind == "scummvm":
        if not any(x == "--config=" + c for x in a):
            raise IsolationError("SCUMMVM_PRIVATE_CONFIG_REQUIRED")
        if not any(x == "--savepath=" + s for x in a):
            raise IsolationError("SCUMMVM_PRIVATE_SAVES_REQUIRED")
    elif kind == "godot":
        if "--path" not in a:
            raise IsolationError("GODOT_EXPLICIT_PROJECT_PATH_REQUIRED")
    else:
        raise IsolationError("UNSUPPORTED_FIDELITY_RUNTIME_KIND", {"runtime_kind": kind})

def assert_private_outputs(run_dir, source_root):
    r = Path(run_dir).resolve()
    s = Path(source_root).resolve()
    if r == s or s in r.parents:
        raise IsolationError("OUTPUT_INSIDE_READ_ONLY_SOURCE")
    return r
