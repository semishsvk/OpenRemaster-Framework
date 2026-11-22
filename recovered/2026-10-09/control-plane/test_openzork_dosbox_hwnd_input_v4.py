"""Original ZORKDOS HWND-targeted key probe; no global keyboard, no fidelity promotion."""
import json,subprocess,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
import numpy as np
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts
root=Path(__file__).resolve().parents[2]
cp=Path(__file__).resolve().parent
oldjob=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/"openzork-native-dosbox-passive-ca496ab07.json"
assert oldjob.is_file()
job=json.loads(oldjob.read_text(encoding="utf-8"))
run="openzork-dosbox-hwnd-input-"+uuid.uuid4().hex[:9]
job["job_id"]=run;job["task"]="ZORKDOSNativeWindowKeyboardDiagnostic"
job["execution"]["capture_mode"]="targeted_input_diagnostic"
job["execution"]["input_plan"]=[{"at_seconds":8.0,"key":"SPACE"}]
job["execution"]["capture_delay_seconds"]=11.5
job["required_capabilities"]=[
 "runtime.fidelity_isolated","runtime.gui_lease.exclusive","runtime.local_capture",
 "runtime.capture.wgc","input.hwnd_owned_diagnostic"]
jpath=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run+".json")
jpath.write_text(json.dumps(job,indent=2),encoding="utf-8")
oldframe=root/"runtime-test"/"results"/"openzork-native-dosbox-passive-ca496ab07"/"fidelity-isolated"/"capture"/"frame-0001.bmp"
before={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
p=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(jpath)],capture_output=True,text=True,timeout=55)
out=root/"runtime-test"/"results"/run
r=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
change={}
if frame.exists():
 with Image.open(frame) as im:
  image=im.convert("RGB")
  image.save(out/"fidelity-isolated"/"capture"/"frame-0001.png")
  a=np.asarray(image,dtype=np.int16)
 with Image.open(oldframe) as im:
  b=np.asarray(im.convert("RGB"),dtype=np.int16)
 if a.shape==b.shape:
  roi1=a[45:,:,:]
  roi2=b[45:,:,:]
  delta=np.abs(roi1-roi2)
  changed=np.any(delta>25,axis=2)
  change={"dimensions":list(a.shape),
          "mean_abs_rgb":round(float(delta.mean()),4),
          "fraction_pixels_changed":round(float(changed.mean()),5),
          "pixels_changed":int(changed.sum())}
 else:
  change={"dimensions_before":list(b.shape),"dimensions_after":list(a.shape),"shape_changed":True}
after={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
posted=(r.get("owned_input_posted_events") or [])
state_changed=change.get("shape_changed") is True or change.get("fraction_pixels_changed",0)>0.07
passed=(p.returncode==2 and receipt.get("status")=="BLOCKED"
        and r.get("diagnostic_capture_status")=="PASS"
        and r.get("capture_integrity")=="PASS" and r.get("exit_code")==0
        and len(posted)==1 and posted[0]["key"]=="SPACE"
        and posted[0]["global_SendInput_used"] is False and state_changed
        and all(after.get(pid)==ctime for pid,ctime in before.items()))
report={"schema":"OpenZork.NativeDOSBoxOwnedInputStateProbe.v1",
 "date_utc":datetime.now(timezone.utc).isoformat(),
 "status":"STATE_DELTA_DIAGNOSTIC_PASS" if passed else "INPUT_STATE_UNVERIFIED",
 "run_id":run,"process_exit":p.returncode,
 "runtime_exit_code":r.get("exit_code"),
 "hwnd":(r.get("runtime_window") or {}).get("hwnd"),
 "original_zorkdos":"READ_ONLY",
 "sent_key":"SPACE","injection":"WM_KEYDOWN_AND_WM_KEYUP_TO_OWNED_HWND_ONLY",
 "key_event_receipts":posted,"capture_provenance":(r.get("capture_evidence") or {}).get("manifest_sha256"),
 "before_frame_sha256":sha256(oldframe),
 "after_frame_sha256":sha256(frame) if frame.is_file() else None,
 "state_delta":change,"state_changed":state_changed,
 "original_gameplay_replay_verified":False,"fidelity_verified":False,
 "other_processes_before":len(before),
 "other_processes_preserved":sum(after.get(pid)==ctime for pid,ctime in before.items()),
 "failure_reason":r.get("failure_reason"),"result_dir":str(out)}
path=out/"input-state-diagnostic.json"
path.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(path)),ensure_ascii=False))
raise SystemExit(0 if passed else 1)
