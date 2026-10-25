"""Opt-in isolated GUI runtime worker. Never uses Remote Desktop video as evidence.
Fidelity PASS requires both local capture provenance and an independent comparison gate.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

from fidelity_runtime_isolation_v1 import (
    SCHEMA, InteractiveMutex, IsolationError, active_console_session, process_session,
    assert_private_outputs, atomic_json, bind_window, assert_window_owned,
    gui_conflicts, desktop_windows, process_identity, sha256, utc, validate_private_runtime_config,
)
from fidelity_local_capture_wgc_v1 import acquire_bound_wgc_frame
from fidelity_capture_sequence_v1 import acquire_bound_wgc_sequence,validate_capture_schedule
from fidelity_capture_sequence_v2 import acquire_bound_wgc_sequence_v2,validate_capture_schedule_v2
from fidelity_local_audio_loopback_v1 import capture_process_audio
from fidelity_targeted_input_v1 import validate_plan,execute_targeted_plan,has_owned_mouse_action
from fidelity_owned_window_menu_v1 import inspect_bound_window_menu,post_bound_dosboxx_quit
from fidelity_seed_saves_v1 import stage_seed_saves
from fidelity_target_binding_v1 import validate_registered_target,validate_game_config_binding
from fidelity_process_wide_preflight_v7 import console_runtime_process_conflicts

ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "source"
LEASE_RECORD = ROOT / "orchestrator" / "control-plane" / "state" / "fidelity-homepc-owner.json"
KNOWN_BACKENDS = ("windows_graphics_capture", "engine_framebuffer")
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
K = ctypes.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None

class IO_COUNTERS(ctypes.Structure):
    _fields_ = [("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64)]

class BASIC_LIMITS(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]

class EXTENDED_LIMITS(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", BASIC_LIMITS),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]

def attach_job_object(process):
    """On setup failure terminate ONLY the child just launched, never pre-existing runtimes."""
    K.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    K.CreateJobObjectW.restype = wintypes.HANDLE
    K.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    K.SetInformationJobObject.restype = wintypes.BOOL
    K.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    K.AssignProcessToJobObject.restype = wintypes.BOOL
    job_handle = K.CreateJobObjectW(None, None)
    if not job_handle:
        raise IsolationError("JOB_OBJECT_CREATE_FAILED")
    try:
        flags = EXTENDED_LIMITS()
        flags.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not K.SetInformationJobObject(job_handle, 9, ctypes.byref(flags), ctypes.sizeof(flags)):
            raise IsolationError("JOB_OBJECT_LIMIT_FAILED", {"winerror": ctypes.get_last_error()})
        if not K.AssignProcessToJobObject(job_handle, int(process._handle)):
            raise IsolationError("JOB_OBJECT_ASSIGN_FAILED", {"winerror": ctypes.get_last_error()})
        return job_handle
    except BaseException:
        K.CloseHandle(job_handle)
        raise

def template_args(arguments, substitutions):
    result = []
    for arg in arguments:
        val = str(arg)
        for name, target in substitutions.items():
            val = val.replace("{" + name + "}", str(target))
        if "{" in val or "}" in val:
            raise IsolationError("UNRESOLVED_RUNTIME_ARG", {"arg": val})
        result.append(val)
    return result

def _capture_files(base, rows):
    if not isinstance(rows, list) or not rows:
        raise IsolationError("CAPTURE_FRAME_FILES_MISSING")
    verified = []
    for entry in rows:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not isinstance(entry.get("sha256"), str):
            raise IsolationError("CAPTURE_FILE_ENTRY_INVALID")
        rel = Path(entry["path"])
        if rel.is_absolute() or ".." in rel.parts:
            raise IsolationError("CAPTURE_PATH_ESCAPE")
        path = (base / rel).resolve()
        if base.resolve() not in path.parents or not path.is_file() or path.stat().st_size == 0:
            raise IsolationError("CAPTURE_FILE_MISSING")
        if sha256(path) != entry["sha256"]:
            raise IsolationError("CAPTURE_HASH_MISMATCH")
        verified.append({"path": str(path), "sha256": entry["sha256"], "size": path.stat().st_size})
    return verified

def validate_capture(capture_dir, identity, window, token, require_audio):
    manifest_path = capture_dir / "capture-attestation.json"
    if not manifest_path.is_file():
        raise IsolationError("LOCAL_CAPTURE_ATTESTATION_MISSING")
    m = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if m.get("schema") != "FidelityLocalCaptureAttestation.v1":
        raise IsolationError("CAPTURE_SCHEMA_INVALID")
    for name, expected in (
        ("run_token", token),
        ("pid", identity["pid"]),
        ("creation_ticks_100ns", identity["creation_ticks_100ns"]),
        ("hwnd", window["hwnd"]),
        ("executable_sha256", identity["executable_sha256"]),
    ):
        if m.get(name) != expected:
            raise IsolationError("CAPTURE_OWNER_MISMATCH", {"field": name})
    if m.get("backend") not in KNOWN_BACKENDS or m.get("remote_desktop_capture_authority") is not False:
        raise IsolationError("UNTRUSTED_CAPTURE_BACKEND")
    frames = _capture_files(capture_dir, m.get("frames"))
    sequence_verification=None
    if m.get("capture_schedule_schema"):
        variant=m["capture_schedule_schema"]
        if variant=="OpenRemaster.BoundedFrameSchedule.v2":
            from fidelity_capture_sequence_v2 import verify_bounded_wgc_sequence_v2
            sequence_verification=verify_bounded_wgc_sequence_v2(capture_dir,m)
        elif variant=="OpenRemaster.BoundedFrameSchedule.v1":
            from fidelity_capture_sequence_v1 import verify_bounded_wgc_sequence
            sequence_verification=verify_bounded_wgc_sequence(capture_dir,m)
        else:
            raise IsolationError("CAPTURE_SEQUENCE_VERSION_NOT_ALLOWED")
    audio = []
    if require_audio:
        if m.get("audio_backend") != "process_loopback":
            raise IsolationError("PROCESS_BOUND_AUDIO_REQUIRED")
        audio = _capture_files(capture_dir, m.get("audio"))
    elif m.get("audio"):
        audio = _capture_files(capture_dir, m["audio"])
    return {"manifest_sha256": sha256(manifest_path), "frames": frames, "audio": audio,
            "backend": m["backend"], "audio_backend": m.get("audio_backend"),
            "capture_schedule_verification":sequence_verification}

def validate_comparison(capture_dir, capture_evidence):
    """Independent, conservative BYTE_EXACT comparator. Never trust self-declared PASS alone."""
    path = capture_dir / "comparison-attestation.json"
    if not path.is_file():
        raise IsolationError("FIDELITY_COMPARISON_MISSING")
    m = json.loads(path.read_text(encoding="utf-8-sig"))
    if m.get("schema") != "FidelityIndependentComparison.v1" or m.get("status") != "PASS":
        raise IsolationError("FIDELITY_COMPARISON_NOT_PASS")
    if m.get("capture_manifest_sha256") != capture_evidence["manifest_sha256"]:
        raise IsolationError("FIDELITY_COMPARISON_WRONG_CAPTURE")
    if m.get("mode") != "SHA256_BYTE_EXACT" or m.get("comparator") != "FidelityByteExact.v1":
        raise IsolationError("INDEPENDENT_COMPARATOR_NOT_SUPPORTED")
    if not m.get("original_capture_manifest_path") or not m.get("original_capture_manifest_sha256"):
        raise IsolationError("ORIGINAL_CAPTURE_PROVENANCE_MISSING")
    original_manifest = Path(m["original_capture_manifest_path"]).resolve()
    permitted = [ROOT / "output", ROOT / "runtime-test" / "results", ROOT / "validation-captures"]
    if not any(original_manifest.is_relative_to(root.resolve()) for root in permitted):
        raise IsolationError("ORIGINAL_CAPTURE_PATH_NOT_AUTHORIZED")
    if capture_dir.resolve() in original_manifest.parents:
        raise IsolationError("SELF_COMPARISON_FORBIDDEN")
    if not original_manifest.is_file() or sha256(original_manifest) != m["original_capture_manifest_sha256"]:
        raise IsolationError("ORIGINAL_CAPTURE_HASH_INVALID")
    original = json.loads(original_manifest.read_text(encoding="utf-8-sig"))
    if (original.get("schema") != "FidelityLocalCaptureAttestation.v1"
            or original.get("remote_desktop_capture_authority") is not False
            or original.get("backend") not in KNOWN_BACKENDS
            or not all(original.get(k) for k in ("pid", "hwnd", "creation_ticks_100ns", "run_token", "executable_sha256"))):
        raise IsolationError("ORIGINAL_RUNTIME_PROVENANCE_INVALID")
    verified_original = _capture_files(original_manifest.parent, original.get("frames"))
    current = capture_evidence["frames"]
    if len(current) != len(verified_original):
        raise IsolationError("FIDELITY_FRAME_COUNT_MISMATCH")
    if any(a["sha256"] != b["sha256"] for a,b in zip(current, verified_original)):
        raise IsolationError("FIDELITY_BYTE_MISMATCH")
    if capture_evidence.get("audio"):
        expected_audio = _capture_files(original_manifest.parent, original.get("audio"))
        if len(expected_audio) != len(capture_evidence["audio"]):
            raise IsolationError("FIDELITY_AUDIO_COUNT_MISMATCH")
        if any(a["sha256"] != b["sha256"] for a,b in zip(capture_evidence["audio"], expected_audio)):
            raise IsolationError("FIDELITY_AUDIO_BYTE_MISMATCH")
    return {"attestation_sha256": sha256(path),
            "original_capture_manifest_sha256": m["original_capture_manifest_sha256"],
            "mode": "SHA256_BYTE_EXACT",
            "comparator": "FidelityByteExact.v1",
            "verified_frame_count": len(current)}

def run(job, result_root):
    """Return a fail-closed durable result. No GUI runtime is launched on occupied desktop."""
    out = Path(result_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    result = {"schema": "FidelityRuntimeResult.v1", "isolation_schema": SCHEMA,
              "job_id": job.get("job_id"), "project": job.get("project"),
              "status": "BLOCKED", "capture_authority": "LOCAL_ONLY",
              "remote_desktop_capture_authority": False, "started_at": utc(),
              "failure_reason": None, "exit_code": None}
    proc, job_handle = None, None
    lock = None
    epoch = uuid.uuid4().hex
    try:
        if job.get("schema") != "FidelityRuntimeJob.v1":
            raise IsolationError("INVALID_FIDELITY_JOB_SCHEMA")
        kind = job.get("runtime_kind")
        capture_mode=job.get("capture_mode","strict_fidelity")
        if capture_mode not in ("strict_fidelity","passive_diagnostic","targeted_input_diagnostic"):
            raise IsolationError("CAPTURE_MODE_UNSUPPORTED")
        if capture_mode!="targeted_input_diagnostic" and job.get("input_plan"):
            raise IsolationError("OWNED_INPUT_ONLY_ALLOWED_IN_TARGETED_DIAGNOSTIC_MODE")
        result["capture_mode"]=capture_mode
        if kind not in ("dosbox", "scummvm", "godot"):
            raise IsolationError("UNSUPPORTED_FIDELITY_RUNTIME_KIND")
        if not job.get("job_id") or not job.get("project"):
            raise IsolationError("MISSING_JOB_IDENTITY")
        exe = Path(job["executable"]).resolve(strict=True)
        if not exe.is_file() or exe.suffix.lower() != ".exe":
            raise IsolationError("RUNTIME_EXE_INVALID")
        registered=validate_registered_target(job["project"],kind,exe)
        result["registered_target"]={
            "project":registered["project"],
            "runtime_kind":registered["runtime_kind"],
            "classification":registered["classification"],
            "executable_sha256":registered["executable_sha256"],
            "input_authority":registered["input_authority"]}
        if any(ch in job["job_id"] for ch in ("/", "\\", ":")):
            raise IsolationError("JOB_ID_PATH_UNSAFE")
        if job.get("timeout_seconds", 120) < 1 or job.get("timeout_seconds", 120) > 900:
            raise IsolationError("INVALID_TIMEOUT")
        if job.get("require_audio") and not (250<=int(job.get("audio_duration_ms",3000))<=15000):
            raise IsolationError("INVALID_AUDIO_CAPTURE_DURATION")
        delay=float(job.get("capture_delay_seconds",0))
        schedule=job.get("capture_schedule_seconds")
        schedule_version=job.get("capture_schedule_contract","v1")
        if schedule_version not in ("v1","v2_extended"):
            raise IsolationError("CAPTURE_SEQUENCE_VERSION_NOT_ALLOWED")
        if schedule is not None:
            if schedule_version=="v2_extended":
                validate_capture_schedule_v2(schedule,capture_mode)
                if job.get("timeout_seconds",120)<max(schedule)+12:
                    raise IsolationError("EXTENDED_SEQUENCE_TIMEOUT_TOO_SHORT")
            else:
                validate_capture_schedule(schedule,capture_mode)
            if job.get("input_plan"):
                raise IsolationError("CAPTURE_SEQUENCE_MUST_NOT_HAVE_INPUT_EVENTS")
        owned_mouse_long_window=(capture_mode=="targeted_input_diagnostic"
                                 and has_owned_mouse_action(job.get("input_plan"))
                                 and kind=="dosbox" and exe.name.lower()=="dosbox-x.exe")
        max_delay=45 if capture_mode=="passive_diagnostic" or owned_mouse_long_window else 12
        if delay<0 or delay>max_delay:
            raise IsolationError("INVALID_CAPTURE_DELAY")
        if capture_mode=="targeted_input_diagnostic":
            validate_plan(job.get("input_plan"),delay)
        if job.get("capture_backend","windows_graphics_capture")!="windows_graphics_capture":
            raise IsolationError("CAPTURE_PRODUCER_NOT_SUPPORTED")
        if job.get("seed_saves") is not None and kind!="scummvm":
            raise IsolationError("SAVE_SEED_ONLY_ALLOWLISTED_FOR_SCUMMVM")
        assert_private_outputs(out, SOURCE_ROOT)
        if process_session(os.getpid()) != active_console_session():
            raise IsolationError("WORKER_NOT_IN_ACTIVE_CONSOLE_SESSION",
                                 {"worker_session":process_session(os.getpid()),
                                  "active_console_session":active_console_session()})
        run_dir = out / "fidelity-isolated"
        if run_dir.exists():
            raise IsolationError("RUN_ALREADY_EXISTS_NO_OVERWRITE")
        # Atomic OS mutex prevents simultaneous workers from racing.
        lock = InteractiveMutex().acquire()
        result["abandoned_mutex_recovered"] = lock.abandoned
        previous = json.loads(LEASE_RECORD.read_text(encoding="utf-8")) if LEASE_RECORD.is_file() else {}
        if previous.get("status") in ("OWNED", "RUNNING") and previous.get("owner_pid"):
            old = process_identity(previous["owner_pid"])
            if old and old["creation_ticks_100ns"] == previous.get("owner_creation_ticks"):
                raise IsolationError("UNRECONCILED_LIVE_OWNER", {"owner": previous})
        conflicts = gui_conflicts()
        result["preflight_conflicts"] = conflicts
        if conflicts and capture_mode=="strict_fidelity":
            raise IsolationError("FOREIGN_GUI_RUNTIME_PRESENT", {"count": len(conflicts), "conflicts": conflicts[:20]})
        if capture_mode=="strict_fidelity":
            # Visible-HWND enumeration is insufficient: hidden/minimized foreign
            # ScummVM/DOSBox/Godot must also block strict fidelity admission.
            hidden_or_visible=console_runtime_process_conflicts()
            result["process_wide_gui_preflight_count"]=len(hidden_or_visible)
            if hidden_or_visible:
                raise IsolationError("FOREIGN_GUI_RUNTIME_PROCESS_PRESENT",
                    {"count":len(hidden_or_visible),"conflicts":hidden_or_visible[:20]})
        if capture_mode in ("passive_diagnostic","targeted_input_diagnostic"):
            result["foreign_gui_coexistence"]="DIAGNOSTIC_ONLY_NO_GLOBAL_INPUT_NO_FIDELITY"
            result["preflight_diagnostic_window_count"]=len(conflicts)
        run_dir.mkdir()
        config_dir = run_dir / "config"
        saves_dir = run_dir / "saves"
        capture_dir = run_dir / "capture"
        overlay_dir = run_dir / "overlay"
        for directory in (config_dir, saves_dir, capture_dir, overlay_dir):
            directory.mkdir()
        if job.get("seed_saves") is not None:
            result["save_seed_materialization"]=stage_seed_saves(
                saves_dir,job["project"],job["seed_saves"])
            if capture_mode=="strict_fidelity":
                entries=result["save_seed_materialization"]["entries"]
                if not all(x["source_kind"]=="PINNED_EVIDENCE" for x in entries):
                    raise IsolationError("STRICT_FIDELITY_REQUIRES_PINNED_SAVE")
        config_path = config_dir / ("scummvm.ini" if kind == "scummvm" else "runtime.conf")
        if job.get("config_source"):
            original_config = Path(job["config_source"]).resolve(strict=True)
            shutil.copy2(original_config, config_path)
            result["original_config_sha256"] = sha256(original_config)
        else:
            if kind == "dosbox":
                raise IsolationError("DOSBOX_ORACLE_CONFIG_REQUIRED")
            config_path.write_text("", encoding="utf-8")
        replacements = {"private_config": config_path, "private_saves": saves_dir,
                        "private_overlay": overlay_dir, "capture_dir": capture_dir, "run_dir": run_dir}
        if kind=="dosbox":
            raw_config=config_path.read_text(encoding="utf-8-sig",errors="replace")
            for name,value in replacements.items():
                raw_config=raw_config.replace("{"+name+"}",str(value))
            if "{" in raw_config or "}" in raw_config:
                raise IsolationError("DOSBOX_CONFIG_TEMPLATE_UNRESOLVED")
            config_path.write_text(raw_config,encoding="utf-8")
        if kind=="scummvm":
            # Old ScummVM 2.0 displays a first-run UPDATE CONSENT dialog if this key
            # is absent; it masks the actual game HWND. Override only the private copy.
            import re
            cfg_text=config_path.read_text(encoding="utf-8-sig")
            if not re.search(r"(?im)^\s*\[scummvm\]\s*$",cfg_text):
                raise IsolationError("SCUMMVM_GLOBAL_CONFIG_SECTION_MISSING")
            cfg_text,n=re.subn(r"(?im)^\s*updates_check\s*=\s*[^\r\n]*",
                               "updates_check=0",cfg_text)
            if n==0:
                cfg_text=re.sub(r"(?im)^(\s*\[scummvm\]\s*\r?\n)",
                                r"\1updates_check=0\n",cfg_text,count=1)
            config_path.write_text(cfg_text,encoding="utf-8")
            result["private_scummvm_updates_check"]="DISABLED_OFFLINE"
        arguments = template_args(job.get("args", []), replacements)
        validate_private_runtime_config(kind, arguments, config_path, saves_dir, SOURCE_ROOT)
        result["game_source_binding"]=validate_game_config_binding(registered,config_path)
        config_sha = sha256(config_path)
        executable_sha = sha256(exe)
        me = process_identity(os.getpid())
        if not me:
            raise IsolationError("WORKER_IDENTITY_UNKNOWN")
        owner = {"schema": "FidelityRuntimeLease.v1", "status": "OWNED",
                 "epoch": epoch, "job_id": job["job_id"], "project": job["project"],
                 "owner_pid": os.getpid(), "owner_creation_ticks": me["creation_ticks_100ns"],
                 "acquired_at": utc(), "mutex_name": lock.name}
        atomic_json(LEASE_RECORD, owner)
        result["epoch"] = epoch
        env = os.environ.copy()
        env["OPENREMASTER_FIDELITY_RUN_TOKEN"] = epoch
        env["OPENREMASTER_FIDELITY_CAPTURE_DIR"] = str(capture_dir)
        cmd = [str(exe), *arguments]
        result["launch"] = {"command": cmd, "config_sha256": config_sha,
                             "executable_sha256": executable_sha, "private_saves": str(saves_dir)}
        with open(run_dir / "stdout.log", "w", encoding="utf-8") as stdout, open(run_dir / "stderr.log", "w", encoding="utf-8") as stderr:
            proc = subprocess.Popen(cmd, cwd=str(run_dir), env=env, stdout=stdout, stderr=stderr,
                                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            try:
                job_handle = attach_job_object(proc)
            except BaseException:
                proc.terminate()
                proc.wait(timeout=10)
                raise
            ident = process_identity(proc.pid)
            if not ident or os.path.normcase(ident["executable"]) != os.path.normcase(str(exe)):
                raise IsolationError("LAUNCHED_RUNTIME_IDENTITY_INVALID")
            ident["executable_sha256"] = executable_sha
            result["runtime_identity"] = ident
            owner["status"] = "RUNNING"
            owner["runtime_pid"] = proc.pid
            atomic_json(LEASE_RECORD, owner)
            window = None
            window_history=[]
            deadline = time.monotonic() + min(15, job.get("timeout_seconds", 120))
            while time.monotonic() < deadline and proc.poll() is None:
                try:
                    window = bind_window(proc.pid, ident["creation_ticks_100ns"], exe, job.get("window_title_contains"))
                    break
                except IsolationError as e:
                    if e.reason not in ("OWNED_WINDOW_NOT_FOUND",):
                        raise
                    if len(window_history)<12:
                        owned=[{"hwnd":w["hwnd"],"title":w["title"]}
                               for w in desktop_windows() if w["pid"]==proc.pid]
                        sample={"offset_s":round(15-max(0,deadline-time.monotonic()),1),"windows":owned}
                        if not window_history or sample["windows"]!=window_history[-1]["windows"]:
                            window_history.append(sample)
                time.sleep(0.2)
            if not window:
                result["owned_window_history"]=window_history
                raise IsolationError("OWNED_GUI_WINDOW_NOT_BOUND")
            result["runtime_window"] = window
            atomic_json(run_dir / "runtime-identity.json", {"schema": "FidelityRuntimeIdentity.v1",
                        "run_token": epoch, "process": ident, "window": window, "config_sha256": config_sha})
            # A sequence samples the same process/HWND at declared time offsets.
            # It is passive diagnostic only; no state-changing host input or fidelity claim.
            if schedule is not None:
                sampler=acquire_bound_wgc_sequence_v2 if schedule_version=="v2_extended" else acquire_bound_wgc_sequence
                result["local_capture"]=sampler(
                    capture_dir,ident,window,epoch,schedule,proc.poll)
                result["capture_schedule_seconds"]=schedule
                result["capture_sequence_diagnostic_only"]=True
            else:
                # Targeted diagnostic uses ONLY PostMessage to exact verified HWND.
                # In passive mode there are no input events. Neither mode can pass fidelity.
                if capture_mode=="targeted_input_diagnostic":
                    posted,plan_start=execute_targeted_plan(ident,window,job.get("input_plan"),delay,proc.poll)
                    result["owned_input_posted_events"]=posted
                    result["input_delivery_authority"]="POSTED_NOT_GAME_CONSUMPTION_PROOF"
                    delay_until=plan_start+delay
                else:
                    delay_until=time.monotonic()+delay
                while time.monotonic()<delay_until:
                    if proc.poll() is not None:
                        raise IsolationError("RUNTIME_EXITED_BEFORE_SETTLED_CAPTURE")
                    assert_window_owned(window["hwnd"],proc.pid,ident["creation_ticks_100ns"],exe)
                    time.sleep(min(0.2,max(0,delay_until-time.monotonic())))
                result["capture_delay_seconds"]=float(job.get("capture_delay_seconds",0))
                result["local_capture"]=acquire_bound_wgc_frame(capture_dir,ident,window,epoch)
            if job.get("require_audio"):
                result["local_audio"]=capture_process_audio(capture_dir,ident,int(job.get("audio_duration_ms",3000)))
                result["local_capture"]["manifest_sha256"]=result["local_audio"]["manifest_sha256"]
            if kind=="dosbox" and exe.name.lower()=="dosbox-x.exe":
                result["dosboxx_owned_window_menu"]=inspect_bound_window_menu(
                    window["hwnd"],proc.pid,ident["creation_ticks_100ns"],exe)
            if capture_mode in ("passive_diagnostic","targeted_input_diagnostic"):
                # Capture exists and has been checked for ownership/provenance.
                # Diagnostic input posting does not prove gameplay state consumption.
                # No original-vs-reconstruction comparator is claimed.
                proof=validate_capture(capture_dir,ident,window,epoch,bool(job.get("require_audio",False)))
                result["capture_evidence"]=proof
                result["capture_integrity"]="PASS"
                result["comparison_evidence"]=None
                result["comparison_authority"]="NOT_PERFORMED"
                result["diagnostic_capture_only"]=True
                result["status"]="BLOCKED"
                result["failure_reason"]="DIAGNOSTIC_COMPLETE_NOT_FIDELITY_VERIFIED"
                # For DOSBox-X, use only its exact owner-verified Main > Quit command,
                # and only when the task explicitly enables this bounded exit method.
                assert_window_owned(window["hwnd"],proc.pid,ident["creation_ticks_100ns"],exe)
                if exe.name.lower()=="dosbox-x.exe" and job.get("allow_owned_menu_quit") is True:
                    result["owned_dosboxx_menu_quit"]=post_bound_dosboxx_quit(
                        window["hwnd"],proc.pid,ident["creation_ticks_100ns"],exe)
                    try:proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:result["owned_menu_quit_timeout"]=True
                if proc.poll() is None:
                    U=ctypes.WinDLL("user32",use_last_error=True)
                    U.PostMessageW.argtypes=(wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM)
                    U.PostMessageW.restype=wintypes.BOOL
                    result["wm_close_sent_to_owned_window"]=bool(U.PostMessageW(window["hwnd"],0x0010,0,0))
                    if result["wm_close_sent_to_owned_window"]:
                        try:proc.wait(timeout=4)
                        except subprocess.TimeoutExpired:
                            result["graceful_close_timeout"]=True
                result["exit_code"]=proc.returncode
                result["stdout_sha256"]=sha256(run_dir/"stdout.log")
                result["stderr_sha256"]=sha256(run_dir/"stderr.log")
                if proc.returncode != 0:
                    result["diagnostic_capture_status"]="CAPTURE_PASS_RUNTIME_EXIT_NOT_CLEAN"
                    result["failure_reason"]="DIAGNOSTIC_RUNTIME_NOT_CLEANLY_CLOSED"
                    result["failure_details"]={"exit_code":proc.returncode,
                                              "owned_process_terminated_by_job_object":proc.returncode is None}
                else:
                    result["diagnostic_capture_status"]="PASS"
                return result
            until = time.monotonic() + job.get("timeout_seconds", 120)
            while proc.poll() is None and time.monotonic() < until:
                assert_window_owned(window["hwnd"],proc.pid,ident["creation_ticks_100ns"],exe)
                foreign = gui_conflicts(exclude_pids=(proc.pid,))
                if foreign:
                    raise IsolationError("GUI_CONTAMINATION_DURING_RUN", {"conflicts": foreign[:10]})
                owner["last_heartbeat_at"] = utc()
                atomic_json(LEASE_RECORD, owner)
                time.sleep(0.5)
            if proc.poll() is None:
                raise IsolationError("RUNTIME_TIMEOUT")
            result["exit_code"] = proc.returncode
            result["stdout_sha256"] = sha256(run_dir / "stdout.log")
            result["stderr_sha256"] = sha256(run_dir / "stderr.log")
            if proc.returncode != job.get("expected_exit_code", 0):
                raise IsolationError("RUNTIME_EXIT_CODE_MISMATCH")
            evidence = validate_capture(capture_dir, ident, window, epoch, bool(job.get("require_audio", False)))
            result["capture_evidence"] = evidence
            comparison = validate_comparison(capture_dir, evidence)
            result["comparison_evidence"] = comparison
            result["status"] = "PASS"
    except IsolationError as e:
        result["failure_reason"] = e.reason
        result["failure_details"] = e.details
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        result["failure_reason"] = "RUNTIME_SUPERVISOR_ERROR"
        result["failure_details"] = {"type": type(e).__name__, "message": str(e)}
    finally:
        # Kill only the process tree created for this run; no name-based global cleanup.
        if job_handle:
            K.CloseHandle(job_handle)
        if proc is not None:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        if lock is not None:
            if result.get("epoch") == epoch:
                atomic_json(LEASE_RECORD, {"schema": "FidelityRuntimeLease.v1",
                            "status": "RELEASED", "epoch": epoch, "job_id": job.get("job_id"),
                            "released_at": utc(), "result": result["status"]})
            lock.close()
        result["finished_at"] = utc()
        atomic_json(out / "result.json", result)
    return result
