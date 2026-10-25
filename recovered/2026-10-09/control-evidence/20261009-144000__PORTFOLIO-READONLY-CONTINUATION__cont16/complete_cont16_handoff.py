"""Complete CONT16 report without altering game sources or other workspaces."""
from pathlib import Path
import json,hashlib,copy
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-142406__PORTFOLIO-READONLY-CONTINUATION__cont15/READ_ONLY_HANDOFF.json"
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(PREV)=="3511de1dca3186f2b80dc9b3624969cfa1f0c9a2eddd856974b12c763dd3f966"
assert sha(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
old=json.loads(PREV.read_text(encoding="utf-8-sig"))
mdk=json.loads((HERE/"MDK_LEVEL3_TRIANGLE_SOURCE_FIXTURE.json").read_text())
stone=json.loads((HERE/"STONEKEEP_CORRECTED_LEVEL_CALLBACKS.json").read_text())
u8=json.loads((HERE/"U8_USECODE_DIRECT_XREF_SCOPE.json").read_text())
manifest_path=HERE/"manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
assert len(old["portfolio"])==23 and len({p["project"] for p in old["portfolio"]})==23
assert mdk["signed_f3"]==-16 and mdk["indices"]==[125,98,116]
assert mdk["triangle_record_absolute_offset"]==1958392
assert stone["writer_count"]==22 and stone["ret_stub_count"]==20
assert stone["level15"]["callback_va"]=="0x4f861"
assert [x["level"] for x in stone["per_level_map"] if not x["is_one_byte_RET_stub"]]==[3,12]
assert u8["byte_match_count"]==10 and u8["aligned_known_use_count"]==7
assert u8["aligned_direct_pointer_writes"]==1 and u8["shape347_mask_result"]=="0x0"
assert u8["source_flx_positive_mask_controls"]==103 and u8["source_flx_records"]==1431
focus={
 "OpenStonekeep":{
  "status":"LEVEL15_CALLBACK_RET_STATIC_PASS_GENERIC_ACTION_HELPERS_AND_RUNTIME_BLOCKED",
  "progress":"Corrected LE relocation object-base error in prior reports: all 22 callbacks resolved to actual VAs. Twenty RET-only, two nontrivial (levels3 and12). Level15 initializer0x4f69a -> global callback0x4f861, one-byte RET, distinct from cell h415 handler0x4f983.",
  "next":"Bound h415 action0 generic helper 0x3d35e and input pump reachability to additional action2/3 before event8, then validate actual loader replay; no graph promotion until proof.",
  "evidence_class":"SOURCE_STATIC_RELOCATION_CORRECTION_NO_GAME_RUNTIME"
 },
 "OpenMDK1":{
  "status":"AUTHENTIC_LEVEL3_HMO2_TRIANGLE_SOURCE_BOUND_CLIP_REPLAY_BLOCKED",
  "progress":"Pinned authentic original HMO_2 triangle0 at MTO byte1958392, vertex indices125/98/116, signed-f3=-16, three original float3 coords and independent source hashes.",
  "next":"Bind original camera and projected UV for this exact triangle; compare clipping fan raster profile and pixels in admissible captured original runtime.",
  "evidence_class":"SOURCE_AUTHENTIC_GEOMETRY_NOT_RUNTIME_CLIPPING"
 },
 "OpenUltima8":{
  "status":"USECODE_88F6_DIRECT_XREF_SCOPE_CLOSED_ALIAS_RUNTIME_HOLD",
  "progress":"Original code scan found10 literal DS88F6 byte pairs, seven aligned NE125/NE126 direct uses and one direct pointer assignment at NE126:0xbb2. Source entry1 shape347 CLRWATER flags0x40 fail mask0x000f8000, while103 source records pass.",
  "next":"Trace resource vtable and possible indirect/alias table mutation; collect native DS88F6 content and GLOB218 handle at runtime only after admission.",
  "evidence_class":"SOURCE_STATIC_DIRECT_POINTER_REFERENCE_NOT_ALIAS_PROOF"
 }}
portfolio=copy.deepcopy(old["portfolio"])
lanes={p["project"]:p["lane"] for p in portfolio}
for row in portfolio:
    p=row["project"]
    if p in focus:
        row.update(focus[p])
    elif p=="OpenRemasterOrchestrator":
        row.update(status="CONTROL_PLANE_REPORT_ONLY_NOT_NATIVE_ADMITTED",
          progress="CONT16 corrected Stonekeep level callbacks; bound authentic MDK LEVEL3 triangle; scoped U8 source table direct xrefs",
          next="Consume report under existing operation ID; no unrelated warm dispatch or duplicate writer",
          evidence_class="REPORT_ONLY")
    else:row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED"
assert len(portfolio)==23 and {x["project"]:x["lane"] for x in portfolio}==lanes
assert {x["project"] for x in portfolio if x["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(x for x in portfolio if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in portfolio if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in portfolio if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
def emit(name,payload):
    content=(json.dumps(payload,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    p=HERE/name
    if p.exists():assert p.read_bytes()==content,("OUTPUT_CONFLICT",name)
    else:
        with p.open("xb") as f:f.write(content)
    return sha(p)
execution={"game_original_instruction_tests":0,"game_runtime":0,"builds":0,"captures":0,
           "heavy_jobs":0,"source_or_game_worktree_writes":0,
           "production_admission":"NOT_RECHECKED_OR_GRANTED",
           "writer_ticket_lease_or_global_journal_changes":False}
delta={
 "schema":"OpenRemaster.ReadOnlySemanticDelta.v16","iteration_id":"CONT16",
 "operation_id":old["operation_id"],
 "run_id":"20261009-144000__PORTFOLIO-READONLY-CONTINUATION__cont16",
 "registry_sha256":sha(REG),"predecessor_handoff_sha256":sha(PREV),
 "new_focus":focus,
 "original_source_report_sha256":{x:sha(HERE/x) for x in
    ("MDK_LEVEL3_TRIANGLE_SOURCE_FIXTURE.json",
     "STONEKEEP_CORRECTED_LEVEL_CALLBACKS.json",
     "U8_USECODE_DIRECT_XREF_SCOPE.json")},
 "correction":"CONT15 callback values were object1 offsets rather than relocated VAs; superseded here by original LE fixup targets.",
 "evidence_scope":"PASS_SOURCE_RELOCATION_BYTES_AND_CORPUS_DATA_ONLY; no game-instruction/runtime/fidelity PASS",
 "execution":execution,
 "portfolio_entries":23,
 "azrael_retail":"PAUSED_WARM_WAIT_EXTERNAL",
 "azrael_demo":"CLOSED_ARCHIVED",
 "framework_phase1":"FROZEN"
}
delta_sha=emit("SEMANTIC_DELTA.json",delta)
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v16",
 "iteration_id":"CONT16","operation_id":old["operation_id"],"run_id":delta["run_id"],
 "artifact_role":"READ_ONLY_REPORT_NOT_PRODUCTION_ACCEPTANCE_CHECKPOINT",
 "status":"SOURCE_STATIC_RELOCATION_CORRECTION_AND_AUTHENTIC_TRIANGLE_PASS_RUNTIME_HOLD",
 "registry_sha256":sha(REG),"predecessor_handoff_sha256":sha(PREV),
 "semantic_delta_sha256":delta_sha,
 "portfolio":portfolio,"execution":execution,
 "source_evidence":{
   "level_callbacks_relocated":22,"level15_callback_va":"0x4f861",
   "level_ret_stubs":20,"MDK_triangle_sha256":mdk["triangle_record_sha256"],
   "U8_DS88F6_literal_matches":10,"U8_validated_direct_use_sites":7,
   "U8_source_default_shape347_mask_result":0,"U8_usecode_positive_controls":103,
   "original_game_runtime_checks":0
 },
 "reproduce":{
   "stonekeep":"python -B stonekeep_correct_callbacks.py",
   "mdk":"python -B mdk_level3_fixture.py",
   "u8":"python -B u8_usecode_xrefs.py",
   "read_only_source_pins":True,"native_rehydration_contract":False
 },
 "preservation":{"phase1":"FROZEN","retail":"PAUSED","demo":"CLOSED",
                 "roth":"WARM_COMPLETION","native_jobs":0},
 "reported_at_local":manifest.get("created","NOT_PROVIDED")
}
handoff_sha=emit("READ_ONLY_HANDOFF.json",handoff)
names=("mdk_level3_fixture.py","MDK_LEVEL3_TRIANGLE_SOURCE_FIXTURE.json",
       "stonekeep_correct_callbacks.py","STONEKEEP_CORRECTED_LEVEL_CALLBACKS.json",
       "u8_usecode_xrefs.py","U8_USECODE_DIRECT_XREF_SCOPE.json",
       "complete_cont16_handoff.py","SEMANTIC_DELTA.json",
       "READ_ONLY_HANDOFF.json","CONT16_SUMMARY.md")
manifest.update(operation_id=old["operation_id"],iteration_id="CONT16",
                artifact_role="READ_ONLY_SOURCE_REPORT_NOT_NATIVE_ADMISSION",
                predecessor_handoff_sha256=sha(PREV),
                outputs=[{"file":n,"sha256":sha(HERE/n),"role":"STATIC_SOURCE_EVIDENCE_OR_REPORT"}
                         for n in names])
manifest_path.write_text(json.dumps(manifest,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
assert all(sha(HERE/x["file"])==x["sha256"] for x in manifest["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text())["portfolio"])==23
print(json.dumps({
 "status":"PASS_READ_ONLY_CONT16_MANIFEST_AND_23_PORTFOLIO",
 "portfolio":23,"ret_callbacks":20,"MDK_triangle_sha":mdk["triangle_record_sha256"],
 "U8_direct_uses":7,"runtime_tests":0,
 "report_sha256":{n:sha(HERE/n) for n in
                 ("SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT16_SUMMARY.md","manifest.json")},
 "run_id":delta["run_id"]},sort_keys=True))
