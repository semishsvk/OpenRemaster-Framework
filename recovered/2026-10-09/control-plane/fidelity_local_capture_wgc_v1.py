"""Local Windows.Graphics.Capture producer for one attested HWND-bound frame.
No desktop or RDC capture. Does not attest fidelity, only acquisition identity.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import subprocess
from fidelity_runtime_isolation_v1 import (
    IsolationError, assert_window_owned, process_identity, sha256, atomic_json,
)

ROOT=Path(__file__).resolve().parents[2]
BINARY=ROOT/"orchestrator"/"capture-worker"/"capture_window_wgc.exe"

def _read_bmp_dimensions(path):
    with open(path,"rb") as f:
        hdr=f.read(54)
    if len(hdr)!=54 or hdr[:2]!=b"BM":
        raise IsolationError("LOCAL_CAPTURE_INVALID_BMP")
    w,h=struct.unpack_from("<ii",hdr,18)
    if not (0<w<=8192 and -8192<=h<0):
        raise IsolationError("LOCAL_CAPTURE_DIMENSIONS_INVALID")
    expected=54+w*(-h)*4
    if path.stat().st_size!=expected:
        raise IsolationError("LOCAL_CAPTURE_BMP_SIZE_INVALID")
    return w,-h

def acquire_bound_wgc_frame(capture_dir, identity, window, token, timeout_seconds=12):
    """One BMP snapshot; called strictly during the lifespan of owned target GUI."""
    if not BINARY.is_file():
        raise IsolationError("LOCAL_WGC_CAPTURE_BINARY_MISSING")
    if not token or not identity.get("executable_sha256"):
        raise IsolationError("CAPTURE_OWNER_TOKEN_MISSING")
    base=Path(capture_dir).resolve()
    base.mkdir(exist_ok=True,parents=True)
    manifest=base/"capture-attestation.json"
    target=base/"frame-0001.bmp"
    if manifest.exists() or target.exists():
        raise IsolationError("CAPTURE_ALREADY_EXISTS_NO_OVERWRITE")
    assert_window_owned(window["hwnd"],identity["pid"],identity["creation_ticks_100ns"],identity["executable"])
    live=process_identity(identity["pid"])
    if not live or live["creation_ticks_100ns"]!=identity["creation_ticks_100ns"]:
        raise IsolationError("CAPTURE_OWNER_PROCESS_CHANGED")
    argv=[str(BINARY),str(window["hwnd"]),str(identity["pid"]),
          str(identity["creation_ticks_100ns"]),str(target)]
    try:
        proc=subprocess.run(argv,capture_output=True,text=True,timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        raise IsolationError("LOCAL_WGC_CAPTURE_TIMEOUT")
    if proc.returncode!=0:
        raise IsolationError("LOCAL_WGC_CAPTURE_FAILED",
                             {"returncode":proc.returncode,"stderr":proc.stderr[-500:]})
    try:
        native=json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise IsolationError("LOCAL_WGC_RECEIPT_INVALID")
    for name,expect in (("pid",identity["pid"]),("hwnd",window["hwnd"]),
                        ("creation_ticks_100ns",identity["creation_ticks_100ns"])):
        if native.get(name)!=expect:
            raise IsolationError("LOCAL_WGC_RECEIPT_OWNER_MISMATCH",{"field":name})
    if native.get("backend")!="windows_graphics_capture" or native.get("capture_frame_file")!=target.name:
        raise IsolationError("LOCAL_WGC_RECEIPT_BACKEND_INVALID")
    if not target.is_file() or target.stat().st_size<100:
        raise IsolationError("LOCAL_WGC_FRAME_MISSING")
    width,height=_read_bmp_dimensions(target)
    if native.get("width")!=width or native.get("height")!=height:
        raise IsolationError("LOCAL_WGC_FRAME_DIMENSION_MISMATCH")
    assert_window_owned(window["hwnd"],identity["pid"],identity["creation_ticks_100ns"],identity["executable"])
    result={
        "schema":"FidelityLocalCaptureAttestation.v1",
        "backend":"windows_graphics_capture",
        "capture_producer":"OpenRemaster.NativeWGCFrame.v1",
        "producer_executable_sha256":sha256(BINARY),
        "run_token":token,
        "pid":identity["pid"],
        "creation_ticks_100ns":identity["creation_ticks_100ns"],
        "hwnd":window["hwnd"],
        "executable_sha256":identity["executable_sha256"],
        "captured_at":datetime.now(timezone.utc).isoformat(),
        "color_format":"BGRA8_TOPDOWN_BMP",
        "remote_desktop_capture_authority":False,
        "frames":[{"path":target.name,"sha256":sha256(target),
                   "width":width,"height":height,"bytes":target.stat().st_size}]
    }
    atomic_json(manifest,result)
    return {"manifest_path":str(manifest),"manifest_sha256":sha256(manifest),
            "frame_path":str(target),"frame_sha256":sha256(target),
            "dimensions":[width,height],"producer_exe_sha256":result["producer_executable_sha256"]}
