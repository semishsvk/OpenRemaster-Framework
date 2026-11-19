"""Stage supervised ScummVM visual/audio diagnostic against a PINNED immutable save.
No game launched by this staging tool, and no shared staging source/save is used.
"""
from pathlib import Path
import json,hashlib,stat
R=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
exe=R/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
cfg=R/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini"
seed=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"/"znemesis.000"
pin=seed.parent/"pinned-save-manifest.json"
assert all(p.is_file() for p in (exe,cfg,seed,pin))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected="3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc"
assert h(seed)==expected
assert not (seed.stat().st_mode&stat.S_IWRITE)
m=json.loads(pin.read_text(encoding="utf-8-sig"))
assert m["pinned_sha256"]==expected
rid="openzork-pinned-vb30-supervised-sequence-v7-r1"
job={
 "schema":"ORCH-K003.Job.v1",
 "job_id":rid,
 "project":"OpenZork",
 "task":"PinnedVB30OriginalGameDataSupervisedLocalVideoAudio",
 "inputs":[{"path":str(p),"sha256":h(p)} for p in (exe,cfg,seed,pin)],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
                          "runtime.capture.wgc","runtime.local_capture",
                          "audio.process_loopback","runtime.saved_state_seed.copy"],
 "execution":{
     "kind":"fidelity_runtime","runtime_kind":"scummvm",
     "capture_mode":"passive_diagnostic",
     "executable":str(exe),"config_source":str(cfg),
     "seed_saves":[{"path":str(seed),"sha256":expected}],
     "args":["--config={private_config}","--savepath={private_saves}",
             "--no-fullscreen","--save-slot=0","znemesis"],
     "capture_backend":"windows_graphics_capture",
     "capture_schedule_seconds":[3,8,14],
     "window_title_contains":"Zork Nemesis",
     "require_audio":True,"audio_duration_ms":3000,
     "timeout_seconds":45
 },
 "validation":{"expected_exit_code":0},
 "acceptance":{"require_validation_pass":True}
}
out=R/"runtime-test"/"jobs"/"fidelity-vb30-pinned-v7"
out.mkdir(parents=True,exist_ok=True)
jobfile=out/(rid+".json")
if jobfile.exists():raise RuntimeError("PINNED_JOB_ALREADY_STAGED")
jobfile.write_text(json.dumps(job,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"STAGED_NO_GAME_LAUNCHED",
 "run_id":rid,"source_save_sha256":expected,
 "scope":"PINNED_SAVE_COPY_AND_LOCAL_CAPTURE_ONLY",
 "project":"OpenZork",
 "expected_runtime_registry_path":"fidelity-runtime-target-registry.v7.json",
 "job":str(jobfile)},ensure_ascii=False))
