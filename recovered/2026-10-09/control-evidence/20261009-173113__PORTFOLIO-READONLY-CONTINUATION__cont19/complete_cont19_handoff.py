"""Finalize source-static CONT19 handoff for 23 unchanged portfolio lanes.

Only this unique reports folder is modified. Does not launch game runtime,
take fidelity captures, register jobs, mutate source, or alter any writer/lease.
"""
from pathlib import Path
import json,hashlib,copy
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-155120__PORTFOLIO-READONLY-CONTINUATION__cont18/READ_ONLY_HANDOFF.json"
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((HERE/name).read_text(encoding="utf-8-sig"))
def emit(name,obj):
 data=(json.dumps(obj,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode("utf-8")
 p=HERE/name
 if p.exists():assert p.read_bytes()==data,("CONFLICTING_REPORT_BYTES",name)
 else:
  with p.open("xb") as f:f.write(data)
 return hashlib.sha256(data).hexdigest()

assert SHA(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
assert SHA(PREV)=="bf2869e2bd8ea39e5f7f877f94bf934e25cc486cd14f41d8d023f33f7d865248"
old=json.loads(PREV.read_text(encoding="utf-8-sig"))
assert len(old["portfolio"])==23 and len({x["project"] for x in old["portfolio"]})==23
operation=old["operation_id"]
assert operation=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
verification=load("STATIC_VERIFICATION.json")
mdk=load("MDK_TRIANGLE_GROUP_RUNTIME_FILTER.json")
view=load("MDK_VIEW_VECTOR_POINTER_SOURCE.json")
sk=load("STONEKEEP_ACTION0_TILE_SELECTOR.json")
u8=load("U8_USECODE_ALIAS_ARRAY_LIFECYCLE.json")
assert verification["status"]=="PASS_ORIGINAL_SOURCE_OPCODE_AND_PURE_MODEL_FIXTURES"
assert verification["region_count"]==13 and verification["opcode_count"]==71
assert verification["pure_group_fixtures"]==30
assert verification["pure_stone_tile_fixtures"]==9
assert verification["pure_U8_name_index_fixtures"]==4
assert verification["original_game_cpu_instructions_executed"]==0
assert verification["original_game_runtime"] is False and verification["visual_fidelity"] is False
assert mdk["source_total_triangles"]==7205
assert mdk["nonzero_group_source_triangles"]==1044
assert mdk["group0_non_targetable_by_this_function"]==6161
assert mdk["group_counts"]["7"]==186
assert mdk["initial_bit10_set"]==mdk["initial_bit20_set"]==0
assert len(mdk["original_group_change_actions"])==6
assert len(mdk["pure_bitwise_fixtures"])==30
assert view["original_global_pointer"]=="0x4a2468" and view["camera_identity"]=="UNOBSERVED"
assert sk["jump_table_linear_targets"][0]=="0x3c19f"
assert sk["branch_condition"]=="0x3d37c AND AL,2; 0x3d381 JNE0x3d3ee if bit0x02 set"
assert len(sk["pure_tile_byte_branch_fixtures"])==9
assert sk["level15_current_tile_byte"]=="NOT_OBSERVED"
assert u8["source_default_shape347_mask_result"]==0
assert len(u8["pure_name_index_fixtures"])==4
assert u8["original_machine_instructions_executed"]==0 and u8["fidelity_verified"] is False

focus={
 "OpenMDK1":{
  "status":"SOURCE_GROUPED_TRIANGLE_RUNTIME_FLAG_CONTROL_STATIC_PASS_NATIVE_FIDELITY_HOLD",
  "progress":"Original per-triangle group flag management at0x40a704 uses high byte of u32 triangle+0x20 and action0..5 to set/clear bits0x10/0x20. Of7205 original LEVEL3 triangles,6161 have group0 and1044 group1..14; all initial bits0x10/0x20 clear. Consumer0x409860 skips triangles with bit0x10; source viewpoint pointer at0x4a2468 is assigned from function EAX at0x40a6b1 and used for plane dot.",
  "next":"Use bounded original LEVEL3 positive-group case (e.g. group7,186 source triangles) to observe actual group action sequence, current triangle bit0x10, camera/viewpoint pointer, side-selected plane, clipped fan and final pixels via independently captured original runtime. No native work before admission.",
  "evidence_class":"NEW_ORIGINAL_SOURCE_DYNAMIC_FILTER_MECHANISM_AND_CORPUS_CENSUS_NOT_RUNTIME"
 },
 "OpenStonekeep":{
  "status":"SOURCE_H415_ACTION0_TILE_BIT_02_BRANCH_BOUND_REENTRY_EVENT8_HOLD",
  "progress":"Original level15 h415 action0 generic0x3d35e calls0x3c14d selector1. CS relative14-entry jump table at0x3c115 selects0x3c19f, which reads current21-byte map cell byte. Bit0x02 determines level status vs conditional rectangle/area helper0x3d454; no actual live tile byte or transitive no-reentry proven.",
  "next":"Bind original level15 current cell byte for the specific h415 source position, trace0x3d454 and conditional level helpers plus independent input action2/3 before event8 consumption; require original loader replay before E.16 graph promotion.",
  "evidence_class":"NEW_SOURCE_STATIC_MAP_SELECTOR_AND_PURE_TILE_NEGATIVES_NOT_RUNTIME"
 },
 "OpenUltima8":{
  "status":"USECODE_EXPORTED_NAME_POINTER_ARRAY_LIFECYCLE_SOURCE_BOUND_INDIRECT_MUTATION_HOLD",
  "progress":"Original NE130 allocates DS8c0a far-pointer slot array using count*4 and clears it, supports per-slot nulling and freeing/reset. NE126 stores pointer to USECODE shape*13+4 name in array slot; these anchored direct writes target alias table not shape capability flags at +0..3. Default shape347 metadata still fails0x000f8000 mask; other aliases and runtime mutations remain unknown.",
  "next":"Trace other readers/writers of DS8c0a aliases and actual mutable DS88f6 allocation/USECODE interpreter paths; when admitted compare original memory contents for GLOB218 shape347 vs shape128 and grid generation.",
  "evidence_class":"NEW_ORIGINAL_SOURCE_ALIAS_TABLE_LIFECYCLE_NO_NATIVE_MEMORY_PROOF"
 }
}
rows=copy.deepcopy(old["portfolio"])
prior_lanes={x["project"]:x["lane"] for x in rows}
for row in rows:
 p=row["project"]
 if p in focus:
  row.update(focus[p])
 elif p=="OpenRemasterOrchestrator":
  row.update(status="REPORT_ONLY_NO_NEW_NATIVE_ADMISSION",
    progress="CONT19 source-static MDK triangle group filter and view-pointer producer, Stonekeep tile selector branch and U8 USECODE alias-array lifecycle; no production job",
    next="Consume same read-only operation ID, preserve single-writer and project isolation",
    evidence_class="CONTROL_PLANE_REPORT_ONLY_NOT_ACCEPTANCE")
 else:row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED_OR_DISPATCHED"
assert len(rows)==23 and len({x["project"] for x in rows})==23
assert {x["project"]:x["lane"] for x in rows}==prior_lanes
assert {x["project"] for x in rows if x["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(x for x in rows if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in rows if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in rows if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"

receipt_hashes={n:SHA(HERE/n) for n in (
 "STATIC_VERIFICATION.json","MDK_TRIANGLE_GROUP_RUNTIME_FILTER.json",
 "MDK_VIEW_VECTOR_POINTER_SOURCE.json","STONEKEEP_ACTION0_TILE_SELECTOR.json",
 "U8_USECODE_ALIAS_ARRAY_LIFECYCLE.json")}
execution={
 "new_game_instruction_tests":0,"new_game_runtime":0,"new_builds":0,
 "new_fidelity_captures":0,"new_heavy_jobs":0,"source_or_game_worktree_mutations":0,
 "portfolio_registry_modified":False,"writer_ticket_lease_or_journal_modified":False,
 "native_ORCH_K003_K004_admission":"NOT_RECHECKED_OR_GRANTED",
 "global_running_jobs":"NOT_RECOUNTED"
}
delta={
 "schema":"OpenRemaster.ReadOnlySemanticDelta.v19",
 "operation_id":operation,"iteration_id":"CONT19",
 "run_id":"20261009-173113__PORTFOLIO-READONLY-CONTINUATION__cont19",
 "registry_sha256":SHA(REG),"predecessor_handoff_sha256":SHA(PREV),
 "focus":focus,"source_static_receipts_sha256":receipt_hashes,
 "status":"ORIGINAL_SOURCE_GROUP_FLAGS_TILE_SELECTOR_AND_U8_ALIAS_STATIC_PASS_RUNTIME_FIDELITY_HOLD",
 "execution":execution,
 "preservation":{"portfolio":23,"azrael_retail":"PAUSED_WARM_WAIT_EXTERNAL",
  "azrael_demo":"CLOSED_ARCHIVED","roth":"WARM_COMPLETION","phase1":"FROZEN"}
}
delta_sha=emit("SEMANTIC_DELTA.json",delta)
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v19",
 "operation_id":operation,"iteration_id":"CONT19","run_id":delta["run_id"],
 "status":delta["status"],
 "artifact_role":"PERSISTENT_STATIC_EVIDENCE_REPORT_NOT_GAME_RUNTIME_ACCEPTANCE",
 "registry_sha256":SHA(REG),"predecessor_handoff_sha256":SHA(PREV),
 "semantic_delta_sha256":delta_sha,
 "static_verification_sha256":receipt_hashes["STATIC_VERIFICATION.json"],
 "source_evidence_sha256":receipt_hashes,
 "portfolio":rows,"execution":execution,"preservation":delta["preservation"],
 "admission":{"ORCH_K003_K004":"NOT_REQUESTED_OR_GRANTED","native_game_capture_authority":"NOT_INVOLVED",
  "source_hashes_verified":True,"new_writer_or_lease":False},
 "reproduction":{"command":"python -B verify_cont19_static.py",
  "expected_result":verification["status"],
  "report_outputs":"deterministic byte-equality, never overwrite divergent files",
  "not_game_rehydration_contract":True}
}
handoff_sha=emit("READ_ONLY_HANDOFF.json",handoff)
summary="""# OpenRemaster CONT19 — 9 October 2026

**Source-static PASS only. No original game instruction test, runtime,
visual fidelity or native job admission.**
Operation OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56.
Portfolio: 23/23, unchanged 3 FOCUS_READ_ONLY lanes.

## OpenMDK1 — exact mutable triangle group filter

Original 0x40A704 matches source triangle group ID stored in high
byte of the 36-byte record's DWORD at +0x20. It only accepts a
requested group 1..255, scans triangle records in 36-byte strides,
and applies source switch actions0..5:
- 0: set bits 0x30; 1: clear bits0x30;
- 2: set bit0x10; 3: clear bit0x10;
- 4: set bit0x20; 5: clear bit0x20.

Original 0x409860 reads the same +0x20 low byte and tests bit0x10.
A bit set skips the normal per-triangle processing branch.

Across the 7,205 original LEVEL3 triangle records, source groups
are 0..14. Group0: 6,161; groups1..14: 1,044. All source
bit0x10 and bit0x20 values are initially zero. Group7 has186.
Thirty pure action/group models verify mutation and restoration.
No original instruction machine code executed.

The original view vector pointer is assigned from caller EAX at
0x40A6B1 to global0x4A2468; 0x40A6DE invokes the signed-plane
traversal which reads this pointer. No live camera coordinates.

## OpenStonekeep — original selector1 map-byte bit0x02

Level15 h415 action0 → helper0x3D35E calls0x3C14D with EAX=1.
The original 14-entry CS-relative jump table resides at
0x3C115 (original encoded CS offset0x2C115). Selector1
dispatches to0x3C19F, reading byte0 of a map record at
21-byte stride.

Original 0x3D37C masks AL with0x02. Clear bit branches to
level/audio status path; set bit branches to conditional
rectangle/area processing via0x3D454. Nine pure byte-model
cases cover both directions. The actual level15 h415 live tile
byte and transitive staging/reentry are still NOT OBSERVED.

## OpenUltima8 — aliased name pointer array lifetime

NE130 allocates far-pointer array at DS8C0A in count*4 bytes,
zeroes it, can clear individual four-byte slots and eventually
frees/nulls the array. NE126:D97..DC7 publishes the original
USECODE name pointer DS88F6 + shape*13 +4 to those slots.

These *direct anchored writes* modify alias slots, not the
metadata capability flags at source record+0..3. They do
NOT prove the loaded USECODE table immutable to indirect
consumers or scripts. Default CLRWATER shape347 flags0x40
continue to fail 0x000F8000 mask; live memory remains unknown.

## Custody and scope

- Original source code byte regions: 13.
- Original source opcode identity checks: 71.
- Pure model fixtures: MDK1 30, Stonekeep 9, Ultima8 4.
- Original machine instruction tests: 0.
- Native game runtime, builds, captures, heavy dispatch: 0.
- Original corpus, game worktrees, existing writer/tickets/leases,
  canonical journal and portfolio registry untouched.
- Azrael Retail PAUSED, Demo CLOSED, ROTH WARM_COMPLETION.
- Framework Phase1 FROZEN; production admission blocked.
"""
sumfile=HERE/"CONT19_SUMMARY.md"
if sumfile.exists():assert sumfile.read_text(encoding="utf-8")==summary
else:
 with sumfile.open("x",encoding="utf-8") as f:f.write(summary)
names=(
 "verify_cont19_static.py","MDK_TRIANGLE_GROUP_RUNTIME_FILTER.json",
 "MDK_VIEW_VECTOR_POINTER_SOURCE.json","STONEKEEP_ACTION0_TILE_SELECTOR.json",
 "U8_USECODE_ALIAS_ARRAY_LIFECYCLE.json","STATIC_VERIFICATION.json",
 "complete_cont19_handoff.py","SEMANTIC_DELTA.json",
 "READ_ONLY_HANDOFF.json","CONT19_SUMMARY.md")
assert all((HERE/n).exists() for n in names)
manfile=HERE/"manifest.json";man=load("manifest.json")
man.update(operation_id=operation,iteration_id="CONT19",
 artifact_role="ORIGINAL_SOURCE_STATIC_REPORT_NOT_RUNTIME_OR_FIDELITY_ADMISSION",
 predecessor_handoff_sha256=SHA(PREV),
 outputs=[{"file":name,"sha256":SHA(HERE/name),"role":"READ_ONLY_SOURCE_STATIC_REPORT"} for name in names])
manfile.write_text(json.dumps(man,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
assert all(SHA(HERE/x["file"])==x["sha256"] for x in man["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text())["portfolio"])==23
assert SHA(PREV)==delta["predecessor_handoff_sha256"] and SHA(REG)==delta["registry_sha256"]
print(json.dumps({
 "result":"PASS_CONT19_SOURCE_STATIC_AND_23_PROJECT_PORTFOLIO_REPORT_ONLY",
 "report_id":delta["run_id"],
 "outputs":len(man["outputs"]),"source_regions":verification["region_count"],
 "original_opcode_checks":verification["opcode_count"],
 "pure_model_cases":{"MDK":30,"Stonekeep":9,"Ultima8":4},
 "native_game_tests":0,
 "report_hashes":{x:SHA(HERE/x) for x in (
    "STATIC_VERIFICATION.json","SEMANTIC_DELTA.json",
    "READ_ONLY_HANDOFF.json","CONT19_SUMMARY.md","manifest.json")}
},sort_keys=True))
