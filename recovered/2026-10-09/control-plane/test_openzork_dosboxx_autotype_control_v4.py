"""Matched DOSBox-X controls: with internal AUTOTYPE vs without, same capture time.
No global keyboard, does not grant gameplay/fidelity PASS.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,sys,uuid
from PIL import Image
import numpy as np
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts
ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
seed=CP/"examples"/"OpenZork-dosboxx-autotype-oracle-seed.conf"
control=CP/"examples"/"OpenZork-dosboxx-no-autotype-control-seed.conf"
text=seed.read_text(encoding="utf-8")
assert text.count("autotype -w 8 -p 0.4 enter")==1
control.write_text(text.replace("autotype -w 8 -p 0.4 enter\n",""),encoding="utf-8")
prior_id="openzork-dosboxx-autotype-3956dd7a57"
prior=ROOT/"runtime-test"/"results"/prior_id
prior_job=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(prior_id+".json")
template=json.loads(prior_job.read_text())
run_id="openzork-dosboxx-control-no-autotype-"+uuid.uuid4().hex[:8]
job=dict(template)
job["job_id"]=run_id
job["task"]="NativeZORKDOSNoInputMatchedControl"
job["execution"]=dict(template["execution"])
job["execution"]["config_source"]=str(control)
job["inputs"]=[dict(template["inputs"][0]),{"path":str(control),"sha256":sha256(control)}]
jf=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
jf.write_text(json.dumps(job,indent=2))
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
p=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jf)],
                 capture_output=True,text=True,timeout=60)
out=ROOT/"runtime-test"/"results"/run_id
rc=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
result=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
with_auto=prior/"fidelity-isolated"/"capture"/"frame-0001.bmp"
info={}
if frame.is_file():
 with Image.open(frame) as im:
  arr=np.asarray(im.convert("RGB"),dtype=np.int16)
  im.save(out/"fidelity-isolated"/"capture"/"frame-0001.png")
 with Image.open(with_auto) as im:
  ref=np.asarray(im.convert("RGB"),dtype=np.int16)
 if arr.shape==ref.shape:
  delta=np.abs(arr[72:]-ref[72:])
  info={"shape":list(arr.shape),
        "fraction_pixels_different":float(np.mean(np.any(delta>22,axis=2))),
        "mean_absolute_rgb":float(np.mean(delta)),
        "control_rgb_mean":list(np.asarray(arr,dtype=np.float64).mean(axis=(0,1)).round(2)),
        "autotype_rgb_mean":list(np.asarray(ref,dtype=np.float64).mean(axis=(0,1)).round(2))}
 else:info={"shapes_mismatch":[list(arr.shape),list(ref.shape)]}
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
safe=(p.returncode==2 and rc.get("status")=="BLOCKED" and result.get("diagnostic_capture_status")=="PASS"
      and result.get("exit_code")==0 and frame.is_file()
      and all(after.get(pid)==ctime for pid,ctime in before.items()))
report={"schema":"OpenZork.DOSBoxXAutotypeMatchedControl.v1",
"status":"TECHNICAL_CONTROL_PASS_DIFFERENCE_REQUIRES_INSPECTION" if safe else "CONTROL_NOT_VERIFIED",
"date_utc":datetime.now(timezone.utc).isoformat(),
"control_run_id":run_id,"autotype_run_id":prior_id,
"control_seed_sha256":sha256(control),"autotype_seed_sha256":sha256(seed),
"capture_delay_seconds":11.5,"same_emulator_sha256":result.get("runtime_identity",{}).get("executable_sha256")==template["inputs"][0]["sha256"],
"control_frame_sha256":sha256(frame) if frame.is_file() else None,
"autotype_frame_sha256":sha256(with_auto),
"numeric_image_difference":info,
"control_capture":str(out/"fidelity-isolated"/"capture"/"frame-0001.png"),
"audio_compared":False,"emulator_keyboard_autotype_proven_consumed":"NOT_YET",
"source_corpus_modified":False,"prior_gui_preserved":len(before),
"native_exit_code":result.get("exit_code"),"reason":result.get("failure_reason"),
"original_fidelity":"NOT_VERIFIED"}
path=out/"matched-control-report.json"
out.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(path)),ensure_ascii=False))
raise SystemExit(0 if safe else 1)
