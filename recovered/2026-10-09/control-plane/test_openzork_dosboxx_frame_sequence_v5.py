"""Timed three-frame observation of ONE DOSBox-X original ZORKDOS process.
Original read-only corpus and internal AUTOTYPE; no global Windows keyboard.
Technical observation only, original-versus-reconstruction fidelity remains HOLD.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess,sys,uuid
from fidelity_runtime_isolation_v1 import gui_conflicts,sha256

ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
SOURCE_JOB=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/"openzork-dosboxx-late-autotype-e5946df0ec.json"
assert SOURCE_JOB.is_file()
base=json.loads(SOURCE_JOB.read_text(encoding="utf-8"))
run_id="openzork-dosboxx-threepoint-"+uuid.uuid4().hex[:10]
job=base
job["job_id"]=run_id
job["task"]="OriginalZORKDOSMultiTimeFrameDiagnostic"
ex=job["execution"]
assert ex["capture_mode"]=="passive_diagnostic"
ex["capture_delay_seconds"]=0
ex["capture_schedule_seconds"]=[10,26,42]
ex["timeout_seconds"]=70
assert ex["allow_owned_menu_quit"] is True
inp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
inp.parent.mkdir(parents=True,exist_ok=True)
inp.write_text(json.dumps(job,indent=2),encoding="utf-8")
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(inp)],
                    capture_output=True,text=True,timeout=90)
out=ROOT/"runtime-test"/"results"/run_id
result=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
rc=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
validation=json.loads((out/"validation-result.json").read_text()) if (out/"validation-result.json").is_file() else {}
capture=result.get("capture_evidence") or {}
verification=capture.get("capture_schedule_verification") or {}
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
passed=(
  proc.returncode==2 and rc.get("status")=="BLOCKED"
  and result.get("diagnostic_capture_status")=="PASS"
  and result.get("capture_integrity")=="PASS"
  and result.get("exit_code")==0
  and len(capture.get("frames") or [])==3
  and verification.get("status")=="PASS_TECHNICAL_CAPTURE_ONLY"
  and validation.get("status")=="FAIL"
  and all(after.get(pid)==ticks for pid,ticks in before.items())
)
frames=[]
manifest=out/"fidelity-isolated"/"capture"/"capture-attestation.json"
if manifest.is_file():
 master=json.loads(manifest.read_text(encoding="utf-8"))
 for i,row in enumerate(master.get("frames") or [],1):
  image_file=manifest.parent/row["path"]
  frames.append({"index":i,"at":row.get("requested_at_seconds"),
       "actual":row.get("started_at_seconds"),"frame_sha256":row["sha256"],
       "frame_path":str(image_file),"size":image_file.stat().st_size if image_file.is_file() else None})
report={
 "schema":"OpenZork.DOSBoxXThreePointOriginalSequence.v1",
 "status":"TECHNICAL_SEQUENCE_PASS_ORIGINAL_GAME_FIDELITY_HOLD" if passed else "BLOCKED",
 "date_utc":datetime.now(timezone.utc).isoformat(),
 "run_id":run_id,
 "original_dos_exe":"ZORKDOS.EXE",
 "source_read_only":True,
 "runtime_sha256":(result.get("runtime_identity") or {}).get("executable_sha256"),
 "input_schedule":"DOSBOX_X_INTERNAL_AUTOTYPE_ENTER_AFTER_8S",
 "capture_type":"3_LOCAL_WGC_WINDOWS_OF_ONE_PROCESS",
 "capture_schedule_seconds":ex["capture_schedule_seconds"],
 "capture_provenance_manifest":str(manifest),
 "manifest_sha256":capture.get("manifest_sha256"),
 "frames":frames,
 "technical_capture_verification":verification,
 "runtime_exit":result.get("exit_code"),
 "runtime_failure_reason":result.get("failure_reason"),
 "fidelity_validation_status":validation.get("status"),
 "unmanaged_game_gui_before":len(before),
 "unmanaged_gui_processes_unchanged":sum(after.get(pid)==t for pid,t in before.items()),
 "reconstruction_comparison_performed":False,
 "original_game_fidelity":"NOT_VERIFIED",
 "stderr_tail":proc.stderr[-700:],
 "worker_exit_code":proc.returncode
}
out.mkdir(parents=True,exist_ok=True)
receipt=out/"timeline-report.json"
receipt.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"schema":report["schema"],"status":report["status"],
 "run_id":run_id,"frame_offsets":report["capture_schedule_seconds"],
 "actual_offsets":[x.get("actual") for x in frames],
 "frame_sha256":[x.get("frame_sha256") for x in frames],
 "runtime_exit":report["runtime_exit"],"blocked_reason":report["runtime_failure_reason"],
 "foreign_gui_preserved":report["unmanaged_gui_processes_unchanged"],
 "evidence":str(receipt)},ensure_ascii=False))
raise SystemExit(0 if passed else 1)
