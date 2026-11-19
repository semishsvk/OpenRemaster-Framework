"""Original ZORKDOS internal-autotype two-ENTER timing hypothesis.
At most 44s capture in one owned DOSBox-X process; no global input.
The second ENTER might or might not select New Game; require visual evidence.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,uuid,subprocess,sys
from fidelity_runtime_isolation_v1 import sha256,gui_conflicts

ROOT=Path(__file__).resolve().parents[2]
CP=Path(__file__).resolve().parent
original=CP/"examples"/"OpenZork-dosboxx-autotype-oracle-seed.conf"
seed=CP/"examples"/"OpenZork-dosboxx-autotype-two-enters-v5.conf"
original_text=original.read_text(encoding="utf-8")
find="autotype -w 8 -p 0.4 enter"
assert original_text.count(find)==1
seed.write_text(original_text.replace(find,"autotype -w 8 -p 35 enter enter"),encoding="utf-8")
template=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/"openzork-dosboxx-threepoint-c0b9fda589.json"
assert template.is_file()
job=json.loads(template.read_text(encoding="utf-8"))
rid="openzork-dosboxx-two-enters-"+uuid.uuid4().hex[:9]
job["job_id"]=rid
job["task"]="OriginalNativeDOSBoxXInternalSecondEnterHypothesis"
ex=job["execution"]
ex["config_source"]=str(seed)
ex["capture_schedule_seconds"]=[10,39,44]
ex["timeout_seconds"]=72
job["inputs"]=[dict(job["inputs"][0]),{"path":str(seed),"sha256":sha256(seed)}]
jobpath=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(rid+".json")
jobpath.write_text(json.dumps(job,indent=2),encoding="utf-8")
before={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jobpath)],
    capture_output=True,text=True,timeout=95)
out=ROOT/"runtime-test"/"results"/rid
result=json.loads((out/"result.json").read_text()) if (out/"result.json").exists() else {}
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").exists() else {}
evidence=result.get("capture_evidence") or {}
after={x["pid"]:x["creation_ticks_100ns"] for x in gui_conflicts()}
valid=(proc.returncode==2 and receipt.get("status")=="BLOCKED"
  and result.get("diagnostic_capture_status")=="PASS" and result.get("exit_code")==0
  and len(evidence.get("frames") or [])==3
  and all(after.get(pid)==ticks for pid,ticks in before.items()))
row={
 "schema":"OpenZork.DOSBoxXInternalDoubleEnterHypothesis.v1",
 "status":"CAPTURE_PASS_INPUT_HYPOTHESIS_UNCLASSIFIED" if valid else "BLOCKED",
 "run_id":rid,
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "seed_sha256":sha256(seed),"autotype_syntax":"AUTOTYPE -w 8 -p 35 enter enter",
 "second_key_intended_offset_s":43,
 "capture_offsets_s":[10,39,44],
 "captured_frames":[{"path":e.get("path"),"sha256":e.get("sha256")} for e in evidence.get("frames",[])],
 "capture_manifest_sha256":evidence.get("manifest_sha256"),
 "native_runtime_exit":result.get("exit_code"),
 "diagnostic_status":result.get("diagnostic_capture_status"),
 "reason":result.get("failure_reason"),
 "foreign_game_gui_processes_preserved":sum(after.get(pid)==ticks for pid,ticks in before.items()),
 "read_only_game_source":True,
 "new_game_selected":"UNVERIFIED_NEEDS_VISUAL_REVIEW",
 "fidelity":"NOT_VERIFIED"
}
out.mkdir(parents=True,exist_ok=True)
p=out/"two-enters-hypothesis-report.json"
p.write_text(json.dumps(row,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":row["status"],"run":rid,"frame_hashes":[x["sha256"] for x in row["captured_frames"]],"exit":row["native_runtime_exit"],"foreign_gui_preserved":row["foreign_game_gui_processes_preserved"],"evidence":str(p)}))
raise SystemExit(0 if valid else 1)
