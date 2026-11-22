"""CONT17 durable report-only semantic handoff across all 23 lanes.

Runs no game code and mutates ONLY the allocated new CONT17 report folder.
No native job, writer/ticket/lease, global journal or project worktree touched.
"""
from pathlib import Path
import hashlib,json,copy
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-144000__PORTFOLIO-READONLY-CONTINUATION__cont16/READ_ONLY_HANDOFF.json"
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text(encoding="utf-8"))
def emit(name,data):
    blob=(json.dumps(data,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    p=HERE/name
    if p.exists():
        assert p.read_bytes()==blob,("EXISTING_REPORT_CONFLICT",name)
    else:
        with p.open("xb") as f:f.write(blob)
    return hashlib.sha256(blob).hexdigest()
assert SHA(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
assert SHA(PREV)=="1dfa42d16c3214b5f2bb742a31308623e7732dc73e627e20ea642ecb717d83e8"
prev=json.loads(PREV.read_text(encoding="utf-8-sig"))
assert len(prev["portfolio"])==23 and len({p["project"] for p in prev["portfolio"]})==23
operation=prev["operation_id"]
assert operation=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
a=read("MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json")
c=read("MDK_SECONDARY_RANGE_F3_CLASSIFICATION.json")
patch=read("MDK_HMO2_PLANE0_SOLID_PATCH.json")
stone=read("STONEKEEP_H415_ACTION0_DIRECT_CHAIN.json")
u8=read("U8_SHAPE347_MASK_AND_ALIAS_GATE.json")
assert a["total_source_triangles"]==7205 and a["total_covered_unique_triangles"]==7205
assert a["total_primary_records"]==7089 and a["total_secondary_records"]==116
assert a["global_uncovered"]==0 and a["global_duplicate_coverage"]==0
assert sum(len(h["possible_format_problems"]) for h in a["hmos"])==0
assert sum(h["secondary_range_count"] for h in a["hmos"])==45
assert c["primary_total"]==7089 and c["secondary_total"]==116
assert c["secondary_signed_f3_classes"]=={"NEGATIVE":96,"POSITIVE":20}
assert c["primary_signed_f3_classes"]=={"NEGATIVE":5418,"POSITIVE":1547,"ZERO":124}
assert patch["source_triangle_total_unsigned_area"]==604
assert patch["source_all_six_signed_f3"]==-16
assert patch["palette_index_16_rgb888"]==[0,0,0]
assert len(patch["original_triangle_record_SHA256"])==6
assert len(stone["original_opcode_checks"])==41
assert stone["level15_ret_only"] and not stone["runtime_or_fidelity_verified"]
assert stone["source_level15_callback"]=="0x4f861"
assert not stone["no_direct_staging_or_queue_call_in_helper_source_region"] is False
assert len(u8["source_opcode_checks"])==14
assert u8["record_shape347"]["name"]=="CLRWATER"
assert u8["record_shape347"]["flags"]==0x40
assert u8["record_shape347"]["own_FLX_entry_length"]==0
assert u8["Map5_special_potential_count"]==2360
assert u8["positive_control_shape59"]["own_FLX_entry_length"]==180
assert u8["runtime_fidelity_verified"] is False
focus={
 "OpenMDK1":{
    "status":"LEVEL3_ALL_7205_PLANE_TRIANGLE_RANGES_STRUCTURAL_PASS_RUNTIME_FIDELITY_HOLD",
    "progress":"Recovered original LEVEL3 plane 44-byte records with primary and secondary triangle subranges; 7,089 primary plus116 secondary in45 secondary groups, all7,205 triangles exactly covered without duplicates across10 HMO blocks. HMO2 plane0 comprises six authentic coplanar f3=-16 black-palette triangles totaling604 source units squared.",
    "next":"Bind original camera and clipped triangle/plane culling to this authentic HMO2 source patch; compare actual pixels and lifecycle in original runtime after admission. Treat secondary span semantics as UNVERIFIED pending producer/consumer mechanism evidence.",
    "evidence_class":"ORIGINAL_CORPUS_STRUCTURAL_RANGE_AND_PALETTE_SOURCE_PASS_ONLY"
 },
 "OpenStonekeep":{
    "status":"H415_LEVEL15_ACTION0_BOUNDED_DIRECT_RESTAGING_REFUTED_TRANSITIVE_RUNTIME_HOLD",
    "progress":"Independent 41 original opcode checks confirm current level15 callback at0x4f861 is RET and action0 direct dispatch skips h415 action2/3 staging and generic current-cell recall site0x3c446. Helper0x3d35e lacks direct stage/event8 queue calls, but transitive side-effects remain unverified.",
    "next":"Trace remaining indirect helper effects and separate input event action2/3 enqueue interleaving; validate event8 admission/generation and original live loader transition before E16 graph promotion.",
    "evidence_class":"BOUNDED_SOURCE_STATIC_CONTROL_FLOW_NEGATIVE_NOT_RUNTIME"
 },
 "OpenUltima8":{
    "status":"SHAPE347_SOURCE_DEFAULT_USECODE_GATE_NEGATIVE_PLUS_ALIAS_WRITE_CORRECTION_RUNTIME_HOLD",
    "progress":"Original EUSECODE member1 shape347 CLRWATER flags0x40 fail0x000f8000 mask and shape347 has no own source bytecode entry. NE126:c90 branches to returnAL0 before secondary allocation; NE126:cd1/ce2 writes are caller output pointer, not table. All2,360 potential Map5 shape347 source children share conditional base-table negative; dynamic table changes and live population unknown.",
    "next":"Trace runtime table/alias mutations and original resource-loader semantics, then bind actual GLOB218 shape347-vs-shape128 handles and live grid epoch under approved original replay.",
    "evidence_class":"SOURCE_DEFAULT_NEGATIVE_WITH_ORIGINAL_OPCODE_ALIAS_CLARIFICATION"
 }}
portfolio=copy.deepcopy(prev["portfolio"])
lanes={x["project"]:x["lane"] for x in portfolio}
for row in portfolio:
    p=row["project"]
    if p in focus:
        row.update(focus[p])
    elif p=="OpenRemasterOrchestrator":
        row.update(status="CONTROL_PLANE_STATIC_REPORT_ONLY_NATIVE_ADMISSION_BLOCKED",
          progress="CONT17 original LEVEL3 primary+secondary plane-span coverage, original HMO2 f3-black patch, h415 action0 bounded path and U8 source table negative",
          next="Reuse existing operation ID and focused read-only game evidence; no fourth heavy slot or duplicate production writer",
          evidence_class="READ_ONLY_EVIDENCE_REPORT_NOT_ORIGINAL_GAME_ACCEPTANCE")
    else:
        row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED_OR_DISPATCHED"
assert len(portfolio)==23 and len({x["project"] for x in portfolio})==23
assert {x["project"]:x["lane"] for x in portfolio}==lanes
assert {x["project"] for x in portfolio if x["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(x for x in portfolio if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in portfolio if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in portfolio if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
sources={
 "registry":SHA(REG),"CONT16_handoff":SHA(PREV),
 "MDK95_EXE":"e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788",
 "MDK_LEVEL3_MTO":a["MTO_sha256"],
 "MDK_level3_font_palette":"4b821a9bc4b4fe74151543cd127061f67432b1e79dc769dab36c60ad4769ed9b",
 "MDK_LEVEL3_DTI":"525c1cf9c13ffe78c19b167e78f9d824a4619adf30ce206b0bdba2b344809623",
 "Stonekeep_EXE":stone["original_EXE_sha256"],
 "Ultima8_EXE":u8["inputs_sha256"]["U8.EXE"],
 "Ultima8_EUSECODE_FLX":u8["inputs_sha256"]["EUSECODE.FLX"],
 "Ultima8_TYPEFLAG":u8["inputs_sha256"]["TYPEFLAG.DAT"],
 "Ultima8_Map5_SourceIR":u8["inputs_sha256"]["Map5SourceIR"]
}
evidence_files=[
 "MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json",
 "MDK_SECONDARY_RANGE_F3_CLASSIFICATION.json",
 "MDK_HMO2_PLANE0_SOLID_PATCH.json",
 "STONEKEEP_H415_ACTION0_DIRECT_CHAIN.json",
 "U8_SHAPE347_MASK_AND_ALIAS_GATE.json"
]
evidence_hashes={x:SHA(HERE/x) for x in evidence_files}
validation={
 "schema":"OpenRemaster.CONT17ReadOnlySourceValidation.v1",
 "status":"PASS_ORIGINAL_SOURCE_STRUCTURE_AND_BOUNDED_OPCODE_PURE_MODEL_ONLY",
 "operation_id":operation,"iteration_id":"CONT17",
 "source_sha256_pins":sources,
 "verified_input_reports_sha256":evidence_hashes,
 "MDK_original_HMO_count":10,
 "MDK_original_total_triangles":7205,
 "MDK_verified_plane_covered_triangles":7205,
 "MDK_primary_triangle_slots":7089,
 "MDK_secondary_triangle_slots":116,
 "MDK_secondary_range_count":45,
 "MDK_uncovered_and_duplicate_triangle_slots":0,
 "MDK_HMO2_plane0_original_triangles":6,
 "MDK_HMO2_plane0_source_area":604,
 "MDK_original_SYS_PAL_index16_rgb888":[0,0,0],
 "Stonekeep_bounded_action0_original_opcode_checks":41,
 "Stonekeep_level15_RET":True,
 "U8_special_original_opcode_checks":14,
 "U8_shape347_source_default_capability_mask":0,
 "U8_shape347_per_shape_script_bytes":0,
 "U8_Map5_potential_special_GLOB_count":2360,
 "original_game_CPU_instruction_tests":0,
 "original_game_runtime":0,"builds":0,"fidelity_capture":0,
 "native_admission_granted":False,
 "source_only_scope":"Sources and pure Python structural calculations only; game runtime, effective table mutation, graphical fidelity and candidate promotion unverified."
}
vs=emit("STATIC_VERIFICATION.json",validation)
delta={
 "schema":"OpenRemaster.ReadOnlySemanticDelta.v17",
 "operation_id":operation,"iteration_id":"CONT17",
 "run_id":"20261009-151734__PORTFOLIO-READONLY-CONTINUATION__cont17",
 "registry_sha256":SHA(REG),
 "predecessor_handoff_sha256":SHA(PREV),
 "static_verification_sha256":vs,
 "evidence_hashes":evidence_hashes,
 "focus":focus,
 "status":"SOURCE_STATIC_SEMANTIC_DELTA_COMPLETE_PRODUCTION_AND_FIDELITY_HOLD",
 "execution":{"new_native_jobs":0,"new_game_CPU_instruction_tests":0,
              "new_game_runtime":0,"new_builds":0,"new_fidelity_captures":0,
              "new_heavy_dispatch":0,"source_or_game_worktree_writes":0,
              "journal_ticket_lease_or_writer_changes":False,
              "native_production_admission":"NOT_RECHECKED_OR_GRANTED",
              "global_running_jobs":"NOT_RECOUNTED"},
 "preservation":{"portfolio_records":23,"azrael_retail":"PAUSED_WARM_WAIT_EXTERNAL",
                 "azrael_demo":"CLOSED_ARCHIVED","OpenROTH":"WARM_COMPLETION",
                 "framework_phase1":"FROZEN","other_warm_lanes":"NOT_REPOLLED"}
}
ds=emit("SEMANTIC_DELTA.json",delta)
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v17",
 "operation_id":operation,"iteration_id":"CONT17","run_id":delta["run_id"],
 "status":delta["status"],
 "artifact_role":"PERSISTENT_SOURCE_STATIC_REPORT_NOT_GAME_RUNTIME_ACCEPTANCE",
 "predecessor_handoff_sha256":SHA(PREV),
 "registry_sha256":SHA(REG),
 "static_verification_sha256":vs,
 "semantic_delta_sha256":ds,
 "original_evidence_hashes":evidence_hashes,
 "portfolio":portfolio,
 "execution":delta["execution"],
 "preservation":delta["preservation"],
 "admission":{"ORCH_K003_K004":"NOT_GRANTED_OR_RECHECKED",
              "new_worker_lease":False,"game_capture_oracle":"NOT_RUN",
              "report_only":True},
 "reproduction":{
   "MDK_plane_ranges":"python -B audit_mdk_plane_dual_ranges.py",
   "MDK_secondary":"python -B classify_mdk_secondary_spans.py",
   "MDK_palette":"python -B verify_mdk_plane0_palette.py",
   "Stonekeep":"python -B trace_stonekeep_h415_action0.py",
   "Ultima8":"python -B audit_u8_usecode_shape347.py",
   "output_policy":"Create-only or compare bytes of report-local artifacts",
   "not_game_rehydration_contract":True
 },
 "reported_from_new_output_run_manifest_created":json.loads((HERE/"manifest.json").read_text(encoding="utf-8-sig"))["created"]
}
hs=emit("READ_ONLY_HANDOFF.json",handoff)
summary="""# OpenRemaster CONT17 — read-only semantic continuation

Source-static evidence verified against original corpus, not a native runtime,
pixel-fidelity, playable or release PASS. All 23 portfolio lanes carried forward.

## OpenMDK1 — complete original plane / triangle dual-range WorldIR

The original LEVEL3O.MTO contains 7,205 triangles across ten HMO
blocks. Each 44-byte plane record has primary u16 triangle count/start
at offsets +20/+22 and optional secondary count/start at +24/+26.
The original indexed geometry comprises 7,089 primary and 116
secondary triangles in 45 secondary ranges. Exact source-byte coverage
is 7,205/7,205, no duplicate or orphan triangle indices.
Secondary f3 mix: 96 negative and 20 positive. This does not establish
that the secondary range represents an independent runtime render pass.

HMO_2 plane0: original normal (0,1,0), D=-1046, six indexed
triangles 0..5, signed-f3=-16, total planar area 604 square source
units. Original negative-f3 raster branch selects color index16,
and SYS_PAL in mdkfont.fti matches LEVEL3.DTI first64; original
index16 RGB = (0,0,0). Camera, clipping, culling, live palette,
frame-buffer output and pixel fidelity remain NOT VERIFIED.

## OpenStonekeep — bounded h415 action0 source chain

Original level15 initializer installs callback 0x4F861, a one-byte RET.
A checked 41-instruction source trace from h415 EAX0 via the generic
selector avoids the direct action2/3 staging branch and avoids the
generic current-cell callback recall at 0x3C446. The remaining
0x3D35E block has no direct call to event8 enqueue, h415 staging
or transition commit. Its transitive helpers and independent input
event interleaving remain UNVERIFIED, so E.16 is not promoted.

## OpenUltima8 — shape347 source-default negative and alias correction

Original EUSECODE.FLX member1 has 1,431 13-byte capability records.
Shape347 CLRWATER flags 0x40 yield zero under the 0x000F8000
secondary-allocation mask; the per-shape FLX[347] bytecode entry is
empty. Shape59 is a genuine source positive-control example.
Original NE126:c90 returns failure for this zero mask BEFORE
secondary allocation; NE126:cd1/ce2 writes go to caller output
(BP+0x10), not the USECODE metadata pointer. All 2,360 Map5
potential shape347 children share the base-source negative result.
Actual runtime table replacement, other callbacks, live population
and grid freshness remain UNOBSERVED.

## Provenance, execution and custody

- Source pins: all three EXEs, MDK LEVEL3 MTO/DTI/font,
  Ultima VIII USECODE/TYPEFLAG/Map5 IR, registry and predecessor.
- Reproducible source-only Python reports are in this directory.
- New game instruction tests/runtime/heavy jobs/builds/captures: ZERO.
- Source/worktrees, writer/ticket/lease, registry and shared journal unchanged.
- Azrael Retail PAUSED; Demo CLOSED; ROTH WARM_COMPLETION.
- Framework Phase 1 frozen; ORCH native production admission not granted.
"""
path=HERE/"CONT17_SUMMARY.md"
if path.exists():assert path.read_text(encoding="utf-8")==summary
else:
 with path.open("x",encoding="utf-8") as f:f.write(summary)
artifact_names=[
 "audit_mdk_plane_dual_ranges.py","MDK_LEVEL3_PLANE_TRIANGLE_DUAL_RANGES.json",
 "classify_mdk_secondary_spans.py","MDK_SECONDARY_RANGE_F3_CLASSIFICATION.json",
 "verify_mdk_plane0_palette.py","MDK_HMO2_PLANE0_SOLID_PATCH.json",
 "audit_u8_usecode_shape347.py","U8_SHAPE347_MASK_AND_ALIAS_GATE.json",
 "trace_stonekeep_h415_action0.py","STONEKEEP_H415_ACTION0_DIRECT_CHAIN.json",
 "finalize_cont17_handoff.py","STATIC_VERIFICATION.json",
 "SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT17_SUMMARY.md"
]
assert all((HERE/name).exists() for name in artifact_names)
manifest_path=HERE/"manifest.json"
m=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
m.update(operation_id=operation,iteration_id="CONT17",
         artifact_role="SOURCE_STATIC_REPORT_ONLY_NOT_NATIVE_ADMISSION_OR_FIDELITY",
         predecessor_handoff_sha256=SHA(PREV),
         outputs=[{"file":name,"sha256":SHA(HERE/name),
                   "role":"ORIGINAL_SOURCE_STATIC_EVIDENCE_OR_REPORT"}
                  for name in artifact_names])
manifest_path.write_text(json.dumps(m,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
assert all(SHA(HERE/x["file"])==x["sha256"] for x in m["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text(encoding="utf-8"))["portfolio"])==23
print(json.dumps({
 "status":"PASS_REPORT_STATIC_SOURCE_AND_23_PORTFOLIO_ONLY",
 "portfolio":23,"source_triangles_covered":7205,
 "secondary_spans":45,"secondary_triangles":116,
 "u8_shape347_source_default_mask":0,
 "stonekeep_bounded_opcode_checks":41,
 "original_runtime_tests":0,
 "report_files":len(m["outputs"]),
 "run_id":delta["run_id"],
 "output_sha256":{name:SHA(HERE/name) for name in
  ("STATIC_VERIFICATION.json","SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json",
   "CONT17_SUMMARY.md","manifest.json")}
},sort_keys=True))
