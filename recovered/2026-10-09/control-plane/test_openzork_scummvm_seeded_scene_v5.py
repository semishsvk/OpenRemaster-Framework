"""ScummVM 2.0.0 Zork Nemesis read-only seeded save startup.
Cross-validation only; original DOSBox ZORKDOS original-executable fidelity separate.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess,sys,uuid
import numpy as np
from PIL import Image
from fidelity_runtime_isolation_v1 import gui_conflicts,sha256

ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
exe=ROOT/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
cfg=ROOT/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini"
seed=ROOT/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"saves"/"znemesis.000"
assert exe.is_file() and cfg.is_file() and seed.is_file()
source_sha=sha256(seed)
run="openzork-scummvm-seeded-scene-"+uuid.uuid4().hex[:10]
job={
 "schema":"ORCH-K003.Job.v1","job_id":run,"project":"OpenZork",
 "task":"CrossValidationScummVMSeededSavedStateStartup",
 "inputs":[{"path":str(exe),"sha256":sha256(exe)},
           {"path":str(cfg),"sha256":sha256(cfg)},
           {"path":str(seed),"sha256":source_sha}],
 "required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
      "runtime.capture.wgc","runtime.local_capture","audio.process_loopback",
      "runtime.saved_state_seed.copy"],
 "execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic",
  "runtime_kind":"scummvm","executable":str(exe),"config_source":str(cfg),
  "seed_saves":[{"path":str(seed),"sha256":source_sha}],
  "args":["--config={private_config}","--savepath={private_saves}",
          "--no-fullscreen","--save-slot=0","znemesis"],
  "window_title_contains":"Zork Nemesis",
  "capture_backend":"windows_graphics_capture",
  "capture_delay_seconds":8,"require_audio":True,
  "audio_duration_ms":3000,"timeout_seconds":30},
 "validation":{"expected_exit_code":0}
}
jp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run+".json")
jp.parent.mkdir(exist_ok=True,parents=True);jp.write_text(json.dumps(job,indent=2))
old={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jp)],
                    capture_output=True,text=True,timeout=55)
out=ROOT/"runtime-test"/"results"/run
result=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
picture=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
stats={}
if picture.is_file():
 with Image.open(picture) as img:
  im=img.convert("RGB")
  im.save(picture.with_suffix(".png"))
  data=np.asarray(im,dtype=np.float64)
  stats={"shape":[im.width,im.height],
         "mean_rgb":list(data.mean(axis=(0,1)).round(1)),
         "stdev_rgb":list(data.std(axis=(0,1)).round(1))}
seed_copy=out/"fidelity-isolated"/"saves"/"znemesis.000"
source_unchanged=sha256(seed)==source_sha
seed_proof=(seed_copy.is_file() and sha256(seed_copy)==source_sha and source_unchanged)
new={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
passed=(proc.returncode==2 and receipt.get("status")=="BLOCKED"
  and result.get("diagnostic_capture_status")=="PASS" and
  result.get("capture_integrity")=="PASS" and result.get("exit_code")==0
  and picture.is_file() and bool((result.get("capture_evidence") or {}).get("audio"))
  and seed_proof and all(new.get(k)==v for k,v in old.items()))
report={
 "schema":"OpenZork.ScummVMSeededRuntimeCrossValidation.v1",
 "status":"TECHNICAL_SEEDED_CAPTURE_PASS_GAME_STATE_REVIEW_REQUIRED" if passed else "BLOCKED",
 "run_id":run,"timestamp":datetime.now(timezone.utc).isoformat(),
 "original_saved_state_sha256":source_sha,
 "saved_game_copy_read_only_proof":seed_proof,
 "save_materialization":result.get("save_seed_materialization"),
 "launch_saved_slot":"--save-slot=0",
 "scummvm_runtime_sha256":sha256(exe),
 "native_original_DOS_exe_used":False,
 "cross_validation_not_native_DOS_fidelity":True,
 "runtime_exit_code":result.get("exit_code"),
 "capture_manifest_sha256":(result.get("capture_evidence") or {}).get("manifest_sha256"),
 "audio_sha256":((result.get("capture_evidence") or {}).get("audio") or [{}])[0].get("sha256"),
 "frame_sha256":sha256(picture) if picture.is_file() else None,
 "image":str(picture.with_suffix(".png")) if picture.is_file() else None,
 "image_stats":stats,
 "old_gui_processes_preserved":sum(new.get(k)==v for k,v in old.items()),
 "failed_reason":result.get("failure_reason"),
 "gameplay_or_stable_state":"UNVERIFIED_PENDING_VISUAL_INSPECTION",
 "fidelity":"NOT_VERIFIED"
}
out.mkdir(parents=True,exist_ok=True)
summary=out/"save-seeded-cross-validation.json"
summary.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":report["schema"],"status":report["status"],
"run_id":run,"exit":report["runtime_exit_code"],
"reason":report["failed_reason"],"save_copy_hash_verified":seed_proof,
"image":report["image"],"audio_sha256":report["audio_sha256"],
"other_processes_preserved":report["old_gui_processes_preserved"],
"evidence":str(summary)},ensure_ascii=False))
raise SystemExit(0 if passed else 1)
