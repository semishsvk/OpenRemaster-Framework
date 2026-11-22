"""Bounded multi-time-point local WGC capture from ONE owned original-runtime process.
Technical diagnostic only. Every raw native capture is saved in a separate private folder.
No window activation, global input, remote desktop image or fidelity promotion.
"""
from datetime import datetime,timezone
from pathlib import Path
import time
from fidelity_runtime_isolation_v1 import (
    IsolationError, assert_window_owned, sha256, atomic_json, process_identity,
)
from fidelity_local_capture_wgc_v1 import acquire_bound_wgc_frame, BINARY

def validate_capture_schedule(schedule,mode="passive_diagnostic"):
    if mode!="passive_diagnostic":
        raise IsolationError("CAPTURE_SEQUENCE_REQUIRES_PASSIVE_DIAGNOSTIC")
    if not isinstance(schedule,list) or not 2<=len(schedule)<=5:
        raise IsolationError("CAPTURE_SCHEDULE_LENGTH_INVALID")
    prev=-10.0
    times=[]
    for n,value in enumerate(schedule):
        if type(value) not in (int,float):
            raise IsolationError("CAPTURE_SCHEDULE_NONNUMERIC",{"index":n})
        at=float(value)
        if not (0.5<=at<=44.0) or at-prev<2.0:
            raise IsolationError("CAPTURE_SCHEDULE_UNSAFE_OFFSET",{"index":n,"at":at})
        times.append(at)
        prev=at
    return times

def acquire_bound_wgc_sequence(capture_dir,identity,window,token,schedule,poll_exit):
    times=validate_capture_schedule(schedule)
    base=Path(capture_dir).resolve()
    base.mkdir(parents=True,exist_ok=True)
    master=base/"capture-attestation.json"
    if master.exists():
        raise IsolationError("CAPTURE_SEQUENCE_ALREADY_EXISTS")
    if not token or not identity.get("executable_sha256") or not BINARY.is_file():
        raise IsolationError("CAPTURE_SEQUENCE_OWNER_INVALID")
    start=time.monotonic()
    entries=[]
    first=None
    for i,at in enumerate(times,1):
        due=start+at
        while time.monotonic()<due:
            if poll_exit() is not None:
                raise IsolationError("SEQUENCE_TARGET_EXITED_BEFORE_SAMPLE",{"sample":i})
            assert_window_owned(window["hwnd"],identity["pid"],
                                identity["creation_ticks_100ns"],identity["executable"])
            time.sleep(min(0.12,max(0,due-time.monotonic())))
        if poll_exit() is not None:
            raise IsolationError("SEQUENCE_TARGET_EXITED_AT_SAMPLE",{"sample":i})
        actual=time.monotonic()-start
        if actual-at>1.5:
            raise IsolationError("SEQUENCE_SCHEDULE_DEADLINE_MISSED",
                                 {"sample":i,"late_seconds":round(actual-at,3)})
        sample_folder=base/"samples"/("point-%02d"%i)
        evidence=acquire_bound_wgc_frame(sample_folder,identity,window,token)
        path=Path(evidence["frame_path"])
        metadata={
            "path":str(path.relative_to(base)).replace("\\","/"),
            "sha256":evidence["frame_sha256"],
            "bytes":path.stat().st_size,
            "width":evidence["dimensions"][0],
            "height":evidence["dimensions"][1],
            "sample_index":i,
            "requested_at_seconds":at,
            "started_at_seconds":round(actual,3),
            "sample_manifest_path":str(Path(evidence["manifest_path"]).relative_to(base)).replace("\\","/"),
            "sample_manifest_sha256":evidence["manifest_sha256"]
        }
        entries.append(metadata)
        if first is None:first=evidence
    assert_window_owned(window["hwnd"],identity["pid"],
                        identity["creation_ticks_100ns"],identity["executable"])
    record={
        "schema":"FidelityLocalCaptureAttestation.v1",
        "backend":"windows_graphics_capture",
        "capture_producer":"OpenRemaster.NativeWGCFrame.v1",
        "capture_schedule_schema":"OpenRemaster.BoundedFrameSchedule.v1",
        "run_token":token,
        "pid":identity["pid"],
        "creation_ticks_100ns":identity["creation_ticks_100ns"],
        "hwnd":window["hwnd"],
        "executable_sha256":identity["executable_sha256"],
        "producer_executable_sha256":sha256(BINARY),
        "captured_at":datetime.now(timezone.utc).isoformat(),
        "color_format":"BGRA8_TOPDOWN_BMP",
        "remote_desktop_capture_authority":False,
        "frames":entries
    }
    atomic_json(master,record)
    return {
        "manifest_path":str(master),
        "manifest_sha256":sha256(master),
        "frame_path":first["frame_path"],
        "frame_sha256":first["frame_sha256"],
        "frame_count":len(entries),
        "requested_offsets_seconds":times,
        "frames":entries,
        "producer_exe_sha256":record["producer_executable_sha256"],
        "status":"TECHNICAL_CAPTURE_ONLY_NOT_FIDELITY_VERIFIED"
    }


def verify_bounded_wgc_sequence(base,master_record):
    """Independently hash and owner-check every native sample manifest and frame.
    This proves acquisition consistency, NOT gameplay/fidelity equivalence.
    """
    from json import loads
    base=Path(base).resolve()
    if master_record.get("capture_schedule_schema")!="OpenRemaster.BoundedFrameSchedule.v1":
        raise IsolationError("CAPTURE_SEQUENCE_CONTRACT_MISSING")
    rows=master_record.get("frames")
    if not isinstance(rows,list):
        raise IsolationError("CAPTURE_SEQUENCE_FRAMES_MISSING")
    schedule=validate_capture_schedule([r["requested_at_seconds"] for r in rows])
    if len(rows)!=len(schedule):
        raise IsolationError("CAPTURE_SEQUENCE_FRAME_COUNT_MISMATCH")
    for i,row in enumerate(rows,1):
        if row.get("sample_index")!=i:
            raise IsolationError("CAPTURE_SEQUENCE_FRAME_INDEX_MISMATCH")
        rel=Path(row.get("sample_manifest_path",""))
        if rel.is_absolute() or ".." in rel.parts:
            raise IsolationError("CAPTURE_SEQUENCE_MANIFEST_PATH_UNSAFE")
        path=(base/rel).resolve()
        if base not in path.parents or not path.is_file():
            raise IsolationError("CAPTURE_SEQUENCE_SAMPLE_MANIFEST_MISSING")
        if sha256(path)!=row.get("sample_manifest_sha256"):
            raise IsolationError("CAPTURE_SEQUENCE_SAMPLE_MANIFEST_HASH_MISMATCH")
        sample=loads(path.read_text(encoding="utf-8-sig"))
        if sample.get("schema")!="FidelityLocalCaptureAttestation.v1":
            raise IsolationError("CAPTURE_SEQUENCE_SAMPLE_SCHEMA_INVALID")
        for name in ("run_token","pid","creation_ticks_100ns","hwnd","executable_sha256"):
            if sample.get(name)!=master_record.get(name):
                raise IsolationError("CAPTURE_SEQUENCE_SAMPLE_OWNER_MISMATCH",{"sample":i,"field":name})
        if sample.get("backend")!="windows_graphics_capture" or sample.get("remote_desktop_capture_authority") is not False:
            raise IsolationError("CAPTURE_SEQUENCE_SAMPLE_BACKEND_UNTRUSTED")
        frames=sample.get("frames")
        if not isinstance(frames,list) or len(frames)!=1:
            raise IsolationError("CAPTURE_SEQUENCE_SAMPLE_COUNT_INVALID")
        native_frame=frames[0]
        if native_frame.get("path")!="frame-0001.bmp":
            raise IsolationError("CAPTURE_SEQUENCE_NATIVE_FRAME_UNEXPECTED")
        if native_frame.get("sha256")!=row.get("sha256"):
            raise IsolationError("CAPTURE_SEQUENCE_NATIVE_FRAME_HASH_MISMATCH")
        owned=(path.parent/native_frame["path"]).resolve()
        if base not in owned.parents or not owned.is_file() or sha256(owned)!=row["sha256"]:
            raise IsolationError("CAPTURE_SEQUENCE_NATIVE_FRAME_TAMPERED")
        if not str(owned.relative_to(base)).replace("\\","/")==row.get("path"):
            raise IsolationError("CAPTURE_SEQUENCE_NATIVE_FRAME_PATH_MISMATCH")
        if float(row.get("started_at_seconds",-1))<float(row["requested_at_seconds"])-0.01:
            raise IsolationError("CAPTURE_SEQUENCE_SHOT_TOO_EARLY")
        if float(row["started_at_seconds"])-float(row["requested_at_seconds"])>1.5:
            raise IsolationError("CAPTURE_SEQUENCE_SHOT_TOO_LATE")
    return {"schema":"OpenRemaster.BoundedFrameScheduleVerification.v1",
        "status":"PASS_TECHNICAL_CAPTURE_ONLY","verified_frames":len(rows),
        "original_vs_reconstruction_fidelity":"NOT_TESTED"}
