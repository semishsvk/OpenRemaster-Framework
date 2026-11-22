"""PID-bound process-loopback audio recorder; extends local WGC evidence manifest.
Recording scope is target process tree, never the system render mix.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import subprocess
from fidelity_runtime_isolation_v1 import IsolationError, process_identity, sha256, atomic_json

ROOT=Path(__file__).resolve().parents[2]
BINARY=ROOT/"orchestrator"/"capture-worker"/"capture_process_audio.exe"

def capture_process_audio(capture_dir, identity, duration_ms=3000):
    base=Path(capture_dir).resolve()
    wav=base/"process-0001.wav"
    manifest_path=base/"capture-attestation.json"
    if not manifest_path.is_file() or not BINARY.is_file() or wav.exists():
        raise IsolationError("PROCESS_AUDIO_PREREQUISITE_MISSING")
    if not (250 <= int(duration_ms) <= 15000):
        raise IsolationError("INVALID_PROCESS_AUDIO_DURATION")
    m=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if m.get("schema")!="FidelityLocalCaptureAttestation.v1":
        raise IsolationError("PROCESS_AUDIO_CAPTURE_MANIFEST_INVALID")
    for name in ("pid","creation_ticks_100ns","executable_sha256"):
        if m.get(name)!=identity.get(name):
            raise IsolationError("PROCESS_AUDIO_OWNER_MISMATCH",{"field":name})
    live=process_identity(identity["pid"])
    if not live or live["creation_ticks_100ns"]!=identity["creation_ticks_100ns"]:
        raise IsolationError("PROCESS_AUDIO_TARGET_EXITED")
    args=[str(BINARY),str(identity["pid"]),str(identity["creation_ticks_100ns"]),str(int(duration_ms)),str(wav)]
    try:
        proc=subprocess.run(args,capture_output=True,text=True,timeout=(duration_ms/1000)+14)
    except subprocess.TimeoutExpired:
        raise IsolationError("PROCESS_AUDIO_CAPTURE_TIMEOUT")
    if proc.returncode:
        raise IsolationError("PROCESS_AUDIO_CAPTURE_FAILED",
                             {"returncode":proc.returncode,"stderr":proc.stderr[-600:]})
    try:
        receipt=json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise IsolationError("PROCESS_AUDIO_NATIVE_RECEIPT_INVALID")
    if (receipt.get("schema")!="OpenRemaster.ProcessLoopbackAudio.v1"
            or receipt.get("backend")!="process_loopback"
            or receipt.get("pid")!=identity["pid"]
            or receipt.get("creation_ticks_100ns")!=identity["creation_ticks_100ns"]
            or receipt.get("audio_file")!=wav.name):
        raise IsolationError("PROCESS_AUDIO_NATIVE_OWNER_MISMATCH")
    if not wav.is_file() or wav.stat().st_size<44:
        raise IsolationError("PROCESS_AUDIO_WAV_MISSING")
    with open(wav,"rb") as f:
        hdr=f.read(44)
    if (hdr[:4]!=b"RIFF" or hdr[8:12]!=b"WAVE"
            or hdr[12:16]!=b"fmt " or hdr[36:40]!=b"data"):
        raise IsolationError("PROCESS_AUDIO_WAV_HEADER_INVALID")
    pcm_format,channels,rate=struct.unpack_from("<HHI",hdr,20)
    data_bytes=struct.unpack_from("<I",hdr,40)[0]
    if (pcm_format!=1 or channels!=2 or rate!=44100 or wav.stat().st_size!=44+data_bytes):
        raise IsolationError("PROCESS_AUDIO_FORMAT_INVALID")
    if receipt.get("frames")!=data_bytes//4:
        raise IsolationError("PROCESS_AUDIO_FRAME_COUNT_MISMATCH")
    live=process_identity(identity["pid"])
    if not live or live["creation_ticks_100ns"]!=identity["creation_ticks_100ns"]:
        raise IsolationError("PROCESS_AUDIO_TARGET_CHANGED_POST_CAPTURE")
    m["audio_backend"]="process_loopback"
    m["audio_producer"]="OpenRemaster.ProcessLoopbackAudio.v1"
    m["audio_producer_executable_sha256"]=sha256(BINARY)
    m["audio"]=[{"path":wav.name,"sha256":sha256(wav),"bytes":wav.stat().st_size,
                 "sample_rate":44100,"channels":2,"bits_per_sample":16,
                 "frames":receipt["frames"],"nonzero_samples":receipt.get("nonzero_samples"),
                 "recorded_duration_ms":duration_ms}]
    m["audio_captured_at"]=datetime.now(timezone.utc).isoformat()
    atomic_json(manifest_path,m)
    return {"manifest_sha256":sha256(manifest_path),"audio_file":str(wav),
            "wav_sha256":sha256(wav),"frames":receipt["frames"],
            "nonzero_samples":receipt.get("nonzero_samples"),
            "capture_duration_ms":duration_ms}
