"""Finalize CONT18 read-only source-static evidence; preserves all 23 lanes."""
from pathlib import Path
import json,hashlib,copy

ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PRIOR=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-151734__PORTFOLIO-READONLY-CONTINUATION__cont17/READ_ONLY_HANDOFF.json"
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
SHA=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text(encoding="utf-8-sig"))
def emit(name,obj):
 data=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
 p=HERE/name
 if p.exists():assert p.read_bytes()==data,("REPORT_OUTPUT_CONFLICT",name)
 else:
  with p.open("xb") as f:f.write(data)
 return hashlib.sha256(data).hexdigest()

assert SHA(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
assert SHA(PRIOR)=="a5d86d28b500a614733d028b03f09ed35fdfd7de323269d4e09bcada7ae5b832"
old=json.loads(PRIOR.read_text(encoding="utf-8-sig"))
assert len(old["portfolio"])==23 and len({x["project"] for x in old["portfolio"]})==23
assert old["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
mdk=read("MDK_ORIGINAL_PLANE_SIDE_DISPATCH.json")
sk=read("STONEKEEP_H415_PREHELPER_SCOPE.json")
u8=read("U8_USECODE_NAME_ALIAS_ESCAPE.json")
assert mdk["original_opcode_check_count"]==66
assert len(mdk["source_code_regions"])==7 and len(mdk["pure_finite_side_fixtures"])==12
assert mdk["HMO2_plane0"]["positive_count"]==6 and mdk["HMO2_plane0"]["nonpositive_count"]==0
assert mdk["HMO2_plane128"]["positive_count"]==1 and mdk["HMO2_plane128"]["nonpositive_count"]==6
assert mdk["quantitative_source_scope"]["all_original_LEVEL3_triangles"]==7205
assert sk["original_opcode_check_count"]==35 and len(sk["verified_source_regions"])==7
assert sk["direct_staged_global_writes_found"]==0
assert sk["direct_h415_stage_or_event_queue_calls_found"]==0
assert u8["opcode_check_count"]==34 and len(u8["original_code_byte_regions"])==3
assert u8["source_default_record"]["flags"]=="0x40" and u8["source_default_record"]["result"]==0
assert not mdk["runtime_fidelity"] and not sk["runtime_fidelity_verified"] and not u8["runtime_fidelity_verified"]

focus={
 "OpenMDK1":{
  "status":"MDK_ORIGINAL_FACING_SELECTED_PLANE_TRIANGLES_STATIC_PASS_RUNTIME_HOLD",
  "progress":"Verified source HMO loader0x419ee0, plane signed-dot traversal0x409a6c, +0x14/+0x16 primary for finite dot>0 and +0x18/+0x1a secondary for dot<=0, both consumed by0x409860. Both global traversal modes retain side selection. HMO2 plane0 side counts6/0; plane128 counts1/6; 7205 source triangles remain structurally fully covered.",
  "next":"Admitted original-runtime trace of viewpoint/side selection and actual clipped HMO2 triangles plus authoritative frame pixels; keep side-facing selection game-specific.",
  "evidence_class":"NEW_ORIGINAL_GAME_SOURCE_STATIC_DISPATCH_NOT_RUNTIME"
 },
 "OpenStonekeep":{
  "status":"H415_ACTION0_PREHELPER_DIRECT_STAGE_NEGATIVE_PASS_TRANSITIVE_REENTRY_HOLD",
  "progress":"Seven bounded original helper regions;35 new original opcode checks. Query/map lookups write to caller-provided local output addresses and have no direct calls or writes to h415 staged globals/event8 queue; transitive queries and independent actions remain open.",
  "next":"Identify possible transitive state effects from0xabd3e and generic0x3d35e and any independent action2/3 event interleaving; preserve queue-full negative fixtures before E16 promotion.",
  "evidence_class":"SOURCE_STATIC_NO_DIRECT_STAGE_ONLY"
 },
 "OpenUltima8":{
  "status":"USECODE_SHAPE_NAME_POINTER_ALIAS_STATICALLY_IDENTIFIED_RUNTIME_MUTATION_HOLD",
  "progress":"NE126:D97..DCA writes an alias of USECODE_table+shape*13+4 (name pointer) into DS8C0A pointer array, NE125 likewise passes name pointers to helper.34 opcode checks. This is not a direct write to +0 flags; CLRWATER shape347 base flags0x40 fail mask0x000f8000 but indirect changes remain unverified.",
  "next":"Trace consumers of exported name alias, loaded capability-table lifetime and actual GLOB218 runtime handles/epoch under approved capture; do not infer global immutability.",
  "evidence_class":"SOURCE_STATIC_ALIAS_ESCAPE_NO_NATIVE_MEMORY_READBACK"
 }
}
rows=copy.deepcopy(old["portfolio"])
before={x["project"]:x["lane"] for x in rows}
for row in rows:
 if row["project"] in focus:row.update(focus[row["project"]])
 elif row["project"]=="OpenRemasterOrchestrator":
  row.update(status="CONTROL_PLANE_REPORT_ONLY_PRODUCTION_ADMISSION_BLOCKED",
    progress="CONT18 static original code signed plane-side selector + bounded Stonekeep action0 helpers + U8 name alias",
    next="Reuse single read-only operation identity and original-authoritative project acceptance gates",
    evidence_class="REPORT_ONLY_NO_NATIVE_GAME_JOB")
 else:row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED"
assert len(rows)==23 and {x["project"]:x["lane"] for x in rows}==before
assert {x["project"] for x in rows if x["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(x for x in rows if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in rows if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in rows if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"

evidence_names=("MDK_ORIGINAL_PLANE_SIDE_DISPATCH.json",
 "STONEKEEP_H415_PREHELPER_SCOPE.json","U8_USECODE_NAME_ALIAS_ESCAPE.json")
source_hashes={x:SHA(HERE/x) for x in evidence_names}
receipt={
 "schema":"OpenRemaster.CONT18StaticSourceReceipt.v1",
 "operation_id":old["operation_id"],
 "status":"PASS_ORIGINAL_SOURCE_STATIC_SEMANTICS_AND_PURE_BRANCH_FIXTURES_ONLY",
 "evidence_source_sha256":source_hashes,
 "source_regions":17,"original_opcode_checks":135,"pure_finite_side_cases":12,
 "MDK_runtime_side":{"plane0_positive":6,"plane0_nonpositive":0,
                     "plane128_positive":1,"plane128_nonpositive":6},
 "Stonekeep_direct_staged_writes":0,
 "Stonekeep_direct_event8_calls":0,
 "U8_name_pointer_alias_exported":True,
 "U8_default_shape347_capability_mask_result":0,
 "original_game_instruction_tests":0,"game_runtime_or_fidelity":False,
 "new_builds":0,"new_native_production_admission":False,
 "scope":"Original source opcode and pinned corpus analysis, NOT original gameplay, capture, acceptance or release"
}
r_sha=emit("STATIC_VERIFICATION.json",receipt)
execstat={"new_original_game_instruction_tests":0,"new_game_runtime":0,
 "new_heavy_jobs":0,"new_builds":0,"new_captures":0,
 "source_or_game_worktree_mutations":0,
 "writer_ticket_lease_or_shared_journal_changed":False,
 "native_ORCH_K003_K004_admission":"NOT_RECHECKED_OR_GRANTED",
 "global_running_jobs":"NOT_RECOUNTED"}
delta={
 "schema":"OpenRemaster.ReadOnlySemanticDelta.v18",
 "iteration_id":"CONT18","operation_id":old["operation_id"],
 "run_id":"20261009-155120__PORTFOLIO-READONLY-CONTINUATION__cont18",
 "registry_sha256":SHA(REG),"previous_handoff_sha256":SHA(PRIOR),
 "focus":focus,"original_source_evidence_sha256":source_hashes,
 "static_verification_sha256":r_sha,
 "status":"SOURCE_STATIC_MECHANISMS_PASS_RUNTIME_FIDELITY_HOLD",
 "execution":execstat,
 "preservation":{"portfolio":23,"retail":"PAUSED_WARM_WAIT_EXTERNAL",
                "demo":"CLOSED_ARCHIVED","roth":"WARM_COMPLETION",
                "phase1":"FROZEN"}
}
d_sha=emit("SEMANTIC_DELTA.json",delta)
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v18",
 "operation_id":old["operation_id"],"iteration_id":"CONT18",
 "run_id":delta["run_id"],"status":delta["status"],
 "artifact_role":"READ_ONLY_REPORT_NOT_GAME_ACCEPTANCE_OR_NATIVE_ADMISSION",
 "predecessor_handoff_sha256":SHA(PRIOR),"registry_sha256":SHA(REG),
 "static_verification_sha256":r_sha,"semantic_delta_sha256":d_sha,
 "source_evidence_sha256":source_hashes,"portfolio":rows,
 "execution":execstat,"preservation":delta["preservation"],
 "admission":{"original_runtime_authority":"NOT_INVOLVED",
              "native_production":"NOT_GRANTED","new_writer":False},
 "reproduction":{"mdk":"python -B verify_mdk_original_plane_side.py",
                 "stonekeep":"python -B verify_stonekeep_prehelpers.py",
                 "u8":"python -B verify_u8_usecode_alias.py",
                 "runtime_rehydration_contract":False}
}
h_sha=emit("READ_ONLY_HANDOFF.json",handoff)
summary="""# OpenRemaster CONT18 — original-source semantic continuation

**Static source PASS; NOT native-game replay, pixel fidelity or candidate.**
All 23 portfolio records retained, existing operation ID reused.

## MDK1 — original side-selected triangle ranges

Original MDK95.EXE loader 0x432376→0x419EE0 parses 44-byte plane,
36-byte triangle and 12-byte vertex streams and rebases plane pointer
fields +0x1C/+0x20. Original runtime source loop 0x409A6C computes
d=plane normal dot source view-vector [0x4A2468]+plane D.

Finite d>0: select primary count/start +0x14/+0x16.
Finite d<=0: select opposite-facing count/start +0x18/+0x1A.
This mapping remains in both branches of [0x499F8C]; their
recursion/traversal order differs. Original 0x409860 processes
selected 36-byte triangles, with extra per-triangle filtering.
Do not interpret the secondary span as an independent render pass.

HMO2 plane0 y=1046: positive side six triangles, other side zero.
HMO2 plane128 z=136: positive side one triangle249,
nonpositive side six triangles250..255.
66 pinned original-opcode checks and12 pure finite branch fixtures pass.
The previously confirmed 7205/7205 indexed source coverage remains
structural, not runtime-visible pixel coverage.

## Stonekeep — action0 prehelpers

Original 0x6A183 invokes table/coordinate query and map-byte helpers.
Seven bounded source regions/35 opcode checks verify no direct h415
staged-global writes or event8 enqueue/staging calls.
The queried caller-local output provenance is source-static; other
callee effects and input action2/3 interleaving remain UNVERIFIED.

## Ultima8 — USECODE name-pointer alias

NE126:D97..DCA exports a pointer to DS88F6 + shape*13 +4 (name)
through a runtime pointer array at DS8C0A; NE125 also passes
the name pointer to a far helper. This does not directly write
metadata flags at record+0. Indirect future changes are still
unverified. Shape347 CLRWATER default 0x40 still fails mask
0x000F8000 before the secondary allocation under source-default
table bytes. Original live table/Map5 instance state not observed.

## Execution and custody

17 source-code regions,135 source-opcode checks and12 pure MDK
finite-side fixtures checked. Original game machine-instruction tests,
runtime, builds, captures, heavy dispatch: all ZERO.
Source corpora and project worktrees unchanged.
No ticket/writer/lease/shared journal/register modification.
Azrael Retail PAUSED; Demo CLOSED; ROTH WARM_COMPLETION;
Framework Phase1 FROZEN. Native ORCH production admission not granted.
"""
sum_file=HERE/"CONT18_SUMMARY.md"
if sum_file.exists():assert sum_file.read_text(encoding="utf-8")==summary
else:
 with sum_file.open("x",encoding="utf-8") as f:f.write(summary)
names=("verify_mdk_original_plane_side.py","MDK_ORIGINAL_PLANE_SIDE_DISPATCH.json",
 "verify_stonekeep_prehelpers.py","STONEKEEP_H415_PREHELPER_SCOPE.json",
 "verify_u8_usecode_alias.py","U8_USECODE_NAME_ALIAS_ESCAPE.json",
 "finalize_cont18_handoff.py","STATIC_VERIFICATION.json",
 "SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT18_SUMMARY.md")
assert all((HERE/n).exists() for n in names)
manifest_file=HERE/"manifest.json"
m=json.loads(manifest_file.read_text(encoding="utf-8-sig"))
m.update(operation_id=old["operation_id"],iteration_id="CONT18",
         artifact_role="SOURCE_STATIC_PERSISTENT_REPORT_NOT_ACCEPTANCE",
         predecessor_handoff_sha256=SHA(PRIOR),
         outputs=[{"file":n,"sha256":SHA(HERE/n),
                   "role":"ORIGINAL_SOURCE_STATIC_EVIDENCE_OR_REPORT"} for n in names])
manifest_file.write_text(json.dumps(m,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
assert all(SHA(HERE/x["file"])==x["sha256"] for x in m["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text())["portfolio"])==23
print(json.dumps({
 "result":"PASS_ORIGINAL_SOURCE_STATIC_REPORT_AND_23_PORTFOLIO",
 "run_id":delta["run_id"],"portfolio":23,
 "source_regions":17,"opcode_checks":135,"pure_finite_side_cases":12,
 "game_runtime":0,"files":len(m["outputs"]),
 "hashes":{x:SHA(HERE/x) for x in ("MDK_ORIGINAL_PLANE_SIDE_DISPATCH.json",
        "STONEKEEP_H415_PREHELPER_SCOPE.json","U8_USECODE_NAME_ALIAS_ESCAPE.json",
        "READ_ONLY_HANDOFF.json","STATIC_VERIFICATION.json",
        "CONT18_SUMMARY.md","manifest.json")}
},sort_keys=True))
