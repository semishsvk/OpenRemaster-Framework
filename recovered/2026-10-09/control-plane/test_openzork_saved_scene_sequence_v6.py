"""Three-point ScummVM save-seeded same-scene WGC sequence, read-only source.
This is NOT the original DOSBox game-executable fidelity oracle.
"""
from datetime import datetime,timezone
from pathlib import Path
import json,subprocess,sys,uuid
from fidelity_runtime_isolation_v1 import gui_conflicts,sha256

ROOT=Path(__file__).resolve().parents[2];CP=Path(__file__).resolve().parent
original=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/"openzork-scummvm-seeded-scene-8938d2e819.json"
assert original.is_file()
j=json.loads(original.read_text(encoding="utf-8"))
run_id="openzork-scummvm-golden-scene-sequence-"+uuid.uuid4().hex[:8]
j["job_id"]=run_id
j["task"]="OriginalDataScummVMSeededGoldenSceneStabilityObservation"
ex=j["execution"]
ex["capture_delay_seconds"]=0
ex["capture_schedule_seconds"]=[3,8,14]
ex["timeout_seconds"]=45
assert ex["require_audio"] is True and len(ex["seed_saves"])==1
jp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run_id+".json")
jp.write_text(json.dumps(j,indent=2))
pre={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
proc=subprocess.run([sys.executable,"-B",str(CP/"orch_k003.py"),str(jp)],
                    capture_output=True,text=True,timeout=60)
out=ROOT/"runtime-test"/"results"/run_id
result=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
rc=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
v=json.loads((out/"validation-result.json").read_text()) if (out/"validation-result.json").is_file() else {}
e=result.get("capture_evidence") or {}
frames=e.get("frames") or []
seed_ok=bool(result.get("save_seed_materialization",{}).get("status")=="PASS_SOURCE_READ_ONLY")
post={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
passed=(
 proc.returncode==2 and rc.get("status")=="BLOCKED"
 and result.get("diagnostic_capture_status")=="PASS"
 and result.get("capture_integrity")=="PASS"
 and result.get("exit_code")==0
 and len(frames)==3 and bool(e.get("audio"))
 and seed_ok and v.get("status")=="FAIL"
 and all(post.get(pid)==ctime for pid,ctime in pre.items())
)
report={
 "schema":"OpenZork.ScummVMSeededGoldenSceneMultiFrame.v1",
 "status":"TECHNICAL_CROSSVALIDATION_SEQUENCE_PASS_STATE_STABILITY_UNVERIFIED" if passed else "BLOCKED",
 "run_id":run_id,"captured_at_utc":datetime.now(timezone.utc).isoformat(),
 "source_save_path":ex["seed_saves"][0]["path"],
 "source_save_sha256":ex["seed_saves"][0]["sha256"],
 "save_seed_provenance":result.get("save_seed_materialization"),
 "scummvm_runtime_sha256":(result.get("runtime_identity") or {}).get("executable_sha256"),
 "title_window":result.get("runtime_window"),
 "frame_count":len(frames),
 "frame_hashes":[x.get("sha256") for x in frames],
 "requested_offsets_seconds":ex["capture_schedule_seconds"],
 "capture_schedule_verification":e.get("capture_schedule_verification"),
 "capture_manifest_sha256":e.get("manifest_sha256"),
 "audio_sha256":e["audio"][0].get("sha256") if e.get("audio") else None,
 "runtime_exit":result.get("exit_code"),
 "foreign_processes_preserved":sum(post.get(pid)==ctime for pid,ctime in pre.items()),
 "candidate_same_state_fidelity":"NOT_VERIFIED",
 "original_native_DOS_executable_test":"NOT_THIS_RUN"
}
out.mkdir(parents=True,exist_ok=True)
path=out/"golden-scene-sequence-report.json"
path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"run_id":run_id,
 "offsets":report["requested_offsets_seconds"],"frame_hashes":report["frame_hashes"],
 "seed_copy":seed_ok,"audio_sha256":report["audio_sha256"],
 "runtime_exit":report["runtime_exit"],
 "foreign_pids_unchanged":report["foreign_processes_preserved"],
 "evidence":str(path)}))
raise SystemExit(0 if passed else 1)
