"""Non-destructive Windows canaries for GUI fidelity isolation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fidelity_runtime_isolation_v1 import (
    SCHEMA, InteractiveMutex, IsolationError, active_console_session, process_session,
    bind_window, gui_conflicts, process_identity, sha256, validate_private_runtime_config,
)
from fidelity_runtime_worker_v1 import validate_capture, validate_comparison, _capture_files

def expect(reason, f):
    try:
        f()
    except IsolationError as e:
        assert e.reason == reason, (reason, e.reason)
        return
    raise AssertionError("Expected " + reason)

def test():
    assert os.name == "nt"
    self_identity = process_identity(os.getpid())
    assert self_identity and self_identity["pid"] == os.getpid()
    assert self_identity["creation_ticks_100ns"] > 0
    assert process_session(os.getpid()) == active_console_session(), "Current worker is not on interactive desktop"
    import uuid
    with InteractiveMutex(r"Global\OpenRemaster_FidelityTest_" + uuid.uuid4().hex):
        pass
    name = r"Local\OpenRemaster_FidelityTest_" + uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as d:
        marker = Path(d) / "acquired.txt"
        child = subprocess.Popen([sys.executable, "-B", __file__, "--hold", name, str(marker)],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            until = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < until and child.poll() is None:
                time.sleep(0.05)
            assert marker.exists(), child.communicate()
            expect("GUI_LEASE_BUSY", lambda: InteractiveMutex(name).acquire())
        finally:
            child.wait(timeout=10)
            child.stdout.close()
            child.stderr.close()
        with InteractiveMutex(name):
            pass
        expect("PROCESS_IDENTITY_CHANGED", lambda: bind_window(os.getpid(), 0, "bogus.exe"))
        s = Path(d) / "runtime.conf"
        root = r"F:\Remaster Framework\source"
        s.write_text('[autoexec]\nmount c "F:\\Remaster Framework\\source\\Zork Nemesis"\n')
        expect("SOURCE_MOUNT_NOT_READ_ONLY",
               lambda: validate_private_runtime_config("dosbox", ["-conf", str(s)], s, Path(d)/"saves", root))
        s.write_text('[autoexec]\nmount c "F:\\Remaster Framework\\source\\Zork Nemesis" -ro\n')
        validate_private_runtime_config("dosbox", ["-conf", str(s)], s, Path(d)/"saves", root)
        expect("SCUMMVM_PRIVATE_CONFIG_REQUIRED",
               lambda: validate_private_runtime_config("scummvm", [], s, Path(d)/"saves", root))
        capture_dir = Path(d) / "capture"
        capture_dir.mkdir()
        (capture_dir/"frame.png").write_bytes(b"fake_png_bytes_for_hash_canary")
        fake = {"schema": "FidelityLocalCaptureAttestation.v1", "run_token":"t1",
                "pid": 100, "creation_ticks_100ns": 50, "hwnd": 555,
                "executable_sha256": "exehash", "backend":"remote_desktop_stream",
                "remote_desktop_capture_authority": True,
                "frames":[{"path":"frame.png", "sha256":sha256(capture_dir/"frame.png")}]}
        (capture_dir/"capture-attestation.json").write_text(json.dumps(fake))
        identity = {"pid":100, "creation_ticks_100ns":50, "executable_sha256":"exehash"}
        expect("UNTRUSTED_CAPTURE_BACKEND",
               lambda: validate_capture(capture_dir, identity, {"hwnd":555}, "t1", False))
        fake["backend"] = "windows_graphics_capture"
        fake["remote_desktop_capture_authority"] = False
        fake["pid"] = 999
        (capture_dir/"capture-attestation.json").write_text(json.dumps(fake))
        expect("CAPTURE_OWNER_MISMATCH",
               lambda: validate_capture(capture_dir, identity, {"hwnd":555}, "t1", False))
        fake["pid"] = 100
        fake["frames"][0]["sha256"] = "bad"
        (capture_dir/"capture-attestation.json").write_text(json.dumps(fake))
        expect("CAPTURE_HASH_MISMATCH",
               lambda: validate_capture(capture_dir, identity, {"hwnd":555}, "t1", False))
        fake["frames"][0]["sha256"] = sha256(capture_dir/"frame.png")
        (capture_dir/"capture-attestation.json").write_text(json.dumps(fake))
        proof = validate_capture(capture_dir, identity, {"hwnd":555}, "t1", False)
        expect("FIDELITY_COMPARISON_MISSING", lambda: validate_comparison(capture_dir, proof))
        expect("CAPTURE_PATH_ESCAPE", lambda: _capture_files(capture_dir, [{"path":"../frame.png", "sha256":"bad"}]))
    conflicts = gui_conflicts()
    result={"schema":"FidelityRuntimeIsolationCanary.v1","status":"PASS",
            "mutex_exclusion":"PASS","post_release_reacquisition":"PASS","pid_creation_binding":"PASS",
            "source_mount_guard":"PASS","capture_owner_hash_backend_rejection":"PASS",
            "fidelity_comparison_fail_closed":"PASS","preflight_gui_windows":len(conflicts),
            "preflight_examples":conflicts[:3]}
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    if "--hold" in sys.argv:
        with InteractiveMutex(sys.argv[2]):
            Path(sys.argv[3]).write_text("held")
            time.sleep(2)
    else:
        test()
