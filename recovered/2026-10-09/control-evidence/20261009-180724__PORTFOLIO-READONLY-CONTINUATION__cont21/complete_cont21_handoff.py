"""Finalize scoped CONT21 source-static report, keeping all 23 project lanes."""
from pathlib import Path
import json,hashlib,copy
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-175126__PORTFOLIO-READONLY-CONTINUATION__cont20/READ_ONLY_HANDOFF.json"
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8-sig"))
def emit(p,obj):
    blob=(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
    if p.exists():assert p.read_bytes()==blob,("SOURCE_REPORT_DRIFT",str(p))
    else:
        with p.open("xb") as f:f.write(blob)
    return sha(p)
previous=read(PREV)
delta=read(HERE/"SEMANTIC_DELTA.json")
receipt=read(HERE/"STATIC_VERIFICATION.json")
assert sha(PREV)==delta["predecessor_handoff_sha256"]
assert sha(REG)==delta["registry_sha256"]
assert len(previous["portfolio"])==23 and delta["operation_id"]==previous["operation_id"]
assert set(delta["focus"])=={"OpenMDK1","OpenStonekeep","OpenUltima8"}
assert (receipt["source_region_count"],receipt["opcode_count"])==(5,72)
assert (receipt["MDK_group7_source_members_checked"],receipt["MDK_mask_truth_table_cases"],
        receipt["MDK_pending_pure_cases"])==(186,4,4)
assert receipt["Stonekeep_level_source_table_records"]==23
assert receipt["Ultima8_pure_pointer_cases"]==5
assert receipt["original_game_CPU_instructions_executed"]==0
assert not receipt["native_original_runtime"] and not receipt["fidelity_acceptance"]
rows=copy.deepcopy(previous["portfolio"])
old_lanes={r["project"]:r["lane"] for r in rows}
for row in rows:
    p=row["project"]
    if p in delta["focus"]:row.update(delta["focus"][p])
    elif p=="OpenRemasterOrchestrator":
        row.update(status="CONTROL_PLANE_STATIC_REPORT_ONLY_NATIVE_ADMISSION_HOLD",
                   progress="CONT21 source-static MDK group pending-mask flow, Stonekeep level15 resource pair and U8 alias segment rebase.",
                   next="Preserve single read-only operation ID; no duplicate writer or warm dispatch.",
                   evidence_class="CONTROL_PLANE_REPORT_NOT_GAME_ACCEPTANCE")
    else:row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED"
assert len(rows)==23 and len({r["project"] for r in rows})==23
assert old_lanes=={r["project"]:r["lane"] for r in rows}
assert {r["project"] for r in rows if r["lane"]=="FOCUS_READ_ONLY"}==set(delta["focus"])
assert next(r for r in rows if r["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(r for r in rows if r["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(r for r in rows if r["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
files=("MDK_GROUP7_PENDING_LIFECYCLE.json","STONEKEEP_LEVEL15_RESOURCE_STATUS_PAIR.json",
       "U8_ALIAS_POST_TRANSFER_SEGMENT_REBASE.json","STATIC_VERIFICATION.json")
proof={name:sha(HERE/name) for name in files}
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v21",
 "operation_id":delta["operation_id"],"iteration_id":"CONT21",
 "run_id":delta["run_id"],"status":delta["status"],
 "artifact_role":"ORIGINAL_SOURCE_STATIC_REPORT_ONLY_NOT_NATIVE_FIDELITY_ACCEPTANCE",
 "predecessor_handoff_sha256":sha(PREV),"registry_sha256":sha(REG),
 "semantic_delta_sha256":sha(HERE/"SEMANTIC_DELTA.json"),
 "static_verification_sha256":proof["STATIC_VERIFICATION.json"],
 "source_evidence_sha256":proof,
 "portfolio":rows,"execution":delta["execution"],"preservation":delta["preservation"],
 "admission":{"native_ORCH_K003_K004":"NOT_RECHECKED_OR_GRANTED",
              "original_runtime_capture":"NONE","new_writer_or_lease":False},
 "reproduction":{"command":"python -B verify_cont21_static.py",
                 "source_static_only":True,"byte_deterministic":True,
                 "not_original_game_rehydration_contract":True}
}
hp=HERE/"READ_ONLY_HANDOFF.json"
emit(hp,handoff)
names=("verify_cont21_static.py","MDK_GROUP7_PENDING_LIFECYCLE.json",
       "STONEKEEP_LEVEL15_RESOURCE_STATUS_PAIR.json",
       "U8_ALIAS_POST_TRANSFER_SEGMENT_REBASE.json",
       "STATIC_VERIFICATION.json","SEMANTIC_DELTA.json",
       "CONT21_SUMMARY.md","complete_cont21_handoff.py",
       "READ_ONLY_HANDOFF.json")
assert all((HERE/n).exists() for n in names)
mp=HERE/"manifest.json";manifest=read(mp)
manifest.update(operation_id=delta["operation_id"],iteration_id="CONT21",
    artifact_role="SOURCE_STATIC_READ_ONLY_REPORT_NOT_ACCEPTANCE",
    predecessor_handoff_sha256=sha(PREV),
    outputs=[{"file":n,"sha256":sha(HERE/n),
              "role":"READ_ONLY_SOURCE_EVIDENCE_OR_REPORT"} for n in names])
mp.write_text(json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
assert all(sha(HERE/x["file"])==x["sha256"] for x in manifest["outputs"])
assert len(read(hp)["portfolio"])==23
print(json.dumps({"result":"PASS_CONT21_STATIC_REPORT_AND_23_PORTFOLIO",
 "run_id":delta["run_id"],"portfolio":23,"source_regions":5,"opcode_checks":72,
 "original_game_tests":0,"manifest_outputs":len(manifest["outputs"]),
 "handoff_sha256":sha(hp),"manifest_sha256":sha(mp)},sort_keys=True))
