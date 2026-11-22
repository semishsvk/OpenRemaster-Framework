"""DOSBox-X internal AUTOTYPE original ZORKDOS input, with no host keyboard interaction.
Separate emulator cross-validation from canonical DOSBox 0.74 oracle.
"""
import json,subprocess,sys,uuid
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import numpy as np
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts
root=Path(__file__).resolve().parents[2];cp=Path(__file__).parent
exe=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw\dosbox-x.exe")
cfg=cp/"examples"/"OpenZork-dosboxx-autotype-oracle-seed.conf"
assert exe.is_file() and cfg.is_file()
run="openzork-dosboxx-autotype-"+uuid.uuid4().hex[:10]
job={"schema":"ORCH-K003.Job.v1","job_id":run,"project":"OpenZork",
"task":"NativeZORKDOSInternalAutotypeStateCrossValidation",
"inputs":[{"path":str(exe),"sha256":sha256(exe)},{"path":str(cfg),"sha256":sha256(cfg)}],
"required_capabilities":["runtime.fidelity_isolated","runtime.passive_capture_diagnostic",
 "runtime.capture.wgc","runtime.local_capture","runtime.gui_lease.exclusive"],
"execution":{"kind":"fidelity_runtime","capture_mode":"passive_diagnostic","runtime_kind":"dosbox",
"executable":str(exe),"config_source":str(cfg),
"args":["-conf","{private_config}","-noconsole"],"window_title_contains":"DOSBox-X",
"capture_backend":"windows_graphics_capture","allow_owned_menu_quit":True,
"capture_delay_seconds":11.5,
"require_audio":False,"timeout_seconds":27},
"validation":{"expected_exit_code":0},"acceptance":{"require_validation_pass":True}}
jp=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run+".json")
jp.parent.mkdir(exist_ok=True,parents=True);jp.write_text(json.dumps(job,indent=2))
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(jp)],capture_output=True,text=True,timeout=60)
out=root/"runtime-test"/"results"/run
result=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
info={}
if frame.is_file():
 with Image.open(frame) as img:
  rgb=img.convert("RGB")
  rgb.save(frame.with_suffix(".png"))
  data=np.asarray(rgb,dtype=np.int16)
  info={"dimensions":list(data.shape),"rgb_mean":list(data.mean(axis=(0,1)).round(2)),
        "rgb_std":list(data.std(axis=(0,1)).round(2))}
previous=root/"runtime-test"/"results"/"openzork-native-dosbox-passive-ca496ab07"/"fidelity-isolated"/"capture"/"frame-0001.bmp"
if frame.is_file() and previous.exists():
 with Image.open(previous) as img:
  base=np.asarray(img.convert("RGB"),dtype=np.int16)
 if data.shape==base.shape:
  delta=np.abs(data[46:]-base[46:])
  info["difference_from_dosbox074_prompt"]=float(np.mean(np.any(delta>25,axis=2)))
  info["mean_abs_delta"]=float(delta.mean())
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
safe=(proc.returncode==2 and receipt.get("status")=="BLOCKED"
 and result.get("diagnostic_capture_status")=="PASS" and result.get("exit_code")==0
 and bool(result.get("capture_evidence",{}).get("frames"))
 and all(after.get(pid)==ticks for pid,ticks in before.items()))
report={"schema":"OpenZork.DOSBoxXAutotypeDiagnostic.v1",
"status":"TECHNICAL_CAPTURE_PASS_STATE_NEEDS_VISUAL_INSPECTION" if safe else "BLOCKED",
"run_id":run,"observed_at":datetime.now(timezone.utc).isoformat(),
"executable":str(exe),"executable_sha256":sha256(exe),
"autotype":"AUTOTYPE -w 8 -p 0.4 ENTER in private autoexec",
"source_game_binary":"ORIGINAL_ZORKDOS_EXE_READ_ONLY",
"runtime":"DOSBOX_X_CROSS_VALIDATION_NOT_IDENTICAL_TO_DOSBOX_074",
"native_runtime_exit_code":result.get("exit_code"),
"reason":result.get("failure_reason"),
"capture_manifest_sha256":(result.get("capture_evidence") or {}).get("manifest_sha256"),
"frame_sha256":sha256(frame) if frame.is_file() else None,
"frame_information":info,
"hwnd":(result.get("runtime_window") or {}).get("hwnd"),
"captured_frame_path":str(frame.with_suffix(".png")) if frame.is_file() else None,
"preexisting_gui_processes_preserved":sum(after.get(pid)==ticks for pid,ticks in before.items()),
"preexisting_gui_process_count":len(before),"fidelity_verified":False,
"stdout_tail":proc.stdout[-450:],"stderr_tail":proc.stderr[-450:],
"result_dir":str(out)}
target=out/"dosboxx-autotype-evidence.json";out.mkdir(exist_ok=True,parents=True)
target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(target)),ensure_ascii=False))
raise SystemExit(0 if safe else 1)
