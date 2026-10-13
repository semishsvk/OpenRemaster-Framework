"""CONT20 source-static portfolio handoff. New report dir only."""
from pathlib import Path
import json,copy,hashlib
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-173113__PORTFOLIO-READONLY-CONTINUATION__cont19/READ_ONLY_HANDOFF.json"
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((HERE/name).read_text(encoding="utf-8-sig"))
def emit(name,obj):
    b=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    f=HERE/name
    if f.exists():assert f.read_bytes()==b,("REPORT_CONFLICT",name)
    else:
        with f.open("xb") as w:w.write(b)
    return hashlib.sha256(b).hexdigest()
assert SHA(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
assert SHA(PREV)=="33d24661d1b1df885677aeaa4fbe3bc42e3bfcea6cefc64b72408cf32858202e"
prior=json.loads(PREV.read_text(encoding="utf-8-sig"))
assert len(prior["portfolio"])==23 and len({x["project"] for x in prior["portfolio"]})==23
assert prior["operation_id"]=="OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56"
r=read("STATIC_VERIFICATION.json")
m=read("MDK_GROUP7_VISIBILITY_CONTRACT.json")
members=read("MDK_GROUP7_SOURCE_MEMBERS.json")
sk=read("STONEKEEP_H415_SERIALIZED_TILE_AND_BRANCH.json")
u8=read("U8_USECODE_NAME_POINTER_ARRAY_BOUND.json")
assert r["status"]=="PASS_ORIGINAL_SOURCE_BYTES_OPCODE_AND_PURE_MODEL_FIXTURES_ONLY"
assert (r["source_region_count"],r["opcode_count"])==(14,70)
assert (r["MDK_pure_bitwise_cases"],r["Stonekeep_pure_tile_cases"],r["Ultima8_pure_alias_pointer_cases"])==(35,9,4)
assert r["original_game_machine_instructions_executed"]==0 and not r["original_game_runtime_executed"]
assert (m["source_total_triangles"],m["source_group0"],m["source_nonzero_groups"],m["source_group7"])==(7205,6161,1044,186)
assert m["source_initial_bit10_or20_set_count"]==0
assert len(members["source_instances"])==186
assert sk["h415_source_cell"]["file_offset"]==14081
assert sk["h415_source_cell"]["raw_hex"]=="01008b2d029c9c9f011e0000009cff9cff9cff9cff"
assert sk["h415_source_cell"]["source_test_mask0x02_result"]==0
assert sk["original_level15_callback"]=="0x4F861 one-byte RET"
assert u8["original_shape347_default_flags"]=="0x40"
assert u8["original_shape347_mask_result"]==0

focus={
 "OpenMDK1":{
  "status":"LEVEL3_GROUP_MUTABLE_BIT_SOURCE_PASS_RUNTIME_FIDELITY_HOLD",
  "progress":"Original 36B triangles: group high byte of state at+0x20, action0..5 SET/CLEAR0x30/0x10/0x20; unsigned action>5 defaults CLEAR0x30. Across LEVEL3 source groups0=6161, groups1..14=1044; group7=186 SHA-pinned triangle records; initially all bit0x10/0x20 clear. Renderer0x409860 skips normal path for bit0x10 SET.",
  "next":"Bind original group7 action sequence, live camera/viewpoint0x4A2468 and facing-filtered clipping/pixels, only after native worker admission.",
  "evidence_class":"SOURCE_STATIC_GAME_SPECIFIC_NO_LIVE_GROUP_FLAG"
 },
 "OpenStonekeep":{
  "status":"H415_SOURCE_TILE_BIT02_CLEAR_ACTION0_BRANCH_PASS_LIVE_EVENT8_HOLD",
  "progress":"Original LEVEL01A.SAV cell(23,3) handler415 at offset14081 has byte0=0x01, bit0x02 clear and byte2=0x8B. Under unchanged tile/current position h415 action0 selector1 follows0x3D383 status/audio path; callback level15 0x4F861 is RET. Audio helper0x81D73 and independent action2/3/event8 reentry still open.",
  "next":"Verify actual runtime tile bit before service and transitive helper/event8 generation; no E.16 graph promotion without original loader replay.",
  "evidence_class":"SERIALIZED_SOURCE_TILE_NOT_LIVE_RUNTIME"
 },
 "OpenUltima8":{
  "status":"USECODE_NAME_POINTER_ARRAY_SOURCE_STATIC_PASS_RUNTIME_ALIAS_HOLD",
  "progress":"Original NE130 allocates/zeroes/nulls/frees DS:8C0A array of far name pointers, with NE126 writing shape*13+4 alias. No direct flags +0..3 write from the reviewed routines; source shape347 flags0x40 fail mask0x000F8000, but aliased/runtime table mutation is not ruled out.",
  "next":"Inspect independent consumers of name aliases and original DS:88F6 table lifetime; original GLOB218 paired runtime check only after admission.",
  "evidence_class":"SOURCE_DIRECT_ALIAS_SLOT_NOT_IMMUTABLE_FLAGS_PROOF"
 }}
rows=copy.deepcopy(prior["portfolio"]);original_lanes={x["project"]:x["lane"] for x in rows}
for row in rows:
    project=row["project"]
    if project in focus:row.update(focus[project])
    elif project=="OpenRemasterOrchestrator":
        row.update(status="REPORT_ONLY_NO_NATIVE_PRODUCTION_ADMISSION",
           progress="CONT20 original grouped MDK mutable flags and 186 group7 source triangles; Stonekeep h415 serialized tile; Ultima8 pointer-array lifecycle",
           next="Maintain same operation identity; no duplicate writer or warm-lane dispatch",
           evidence_class="CONTROL_PLANE_READ_ONLY_REPORT")
    else:row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED"
assert len(rows)==23 and len({x["project"] for x in rows})==23
assert {x["project"]:x["lane"] for x in rows}==original_lanes
assert {x["project"] for x in rows if x["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(x for x in rows if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in rows if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in rows if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
source_names=("MDK_GROUP7_VISIBILITY_CONTRACT.json","MDK_GROUP7_SOURCE_MEMBERS.json",
              "STONEKEEP_H415_SERIALIZED_TILE_AND_BRANCH.json",
              "U8_USECODE_NAME_POINTER_ARRAY_BOUND.json","STATIC_VERIFICATION.json")
sources={name:SHA(HERE/name) for name in source_names}
execution={"new_game_machine_instruction_tests":0,"new_game_runtime":0,
  "new_builds":0,"new_captures":0,"new_heavy_jobs":0,
  "original_source_or_game_worktree_writes":0,
  "journal_writer_ticket_lease_or_registry_changes":False,
  "native_ORCH_K003_K004_admission":"NOT_RECHECKED_OR_GRANTED","global_jobs":"NOT_RECOUNTED"}
delta={
 "schema":"OpenRemaster.ReadOnlySemanticDelta.v20",
 "operation_id":prior["operation_id"],"iteration_id":"CONT20",
 "run_id":"20261009-175126__PORTFOLIO-READONLY-CONTINUATION__cont20",
 "registry_sha256":SHA(REG),"predecessor_handoff_sha256":SHA(PREV),
 "status":"SOURCE_STATIC_GROUP_TILE_AND_ALIAS_EVIDENCE_PASS_RUNTIME_FIDELITY_BLOCKED",
 "focus":focus,"source_receipts_sha256":sources,"execution":execution,
 "preservation":{"portfolio_count":23,"retail":"PAUSED_WARM_WAIT_EXTERNAL",
                 "demo":"CLOSED_ARCHIVED","roth":"WARM_COMPLETION",
                 "framework_phase1":"FROZEN"}
}
dsha=emit("SEMANTIC_DELTA.json",delta)
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v20",
 "operation_id":prior["operation_id"],"iteration_id":"CONT20","run_id":delta["run_id"],
 "status":delta["status"],"artifact_role":"SOURCE_STATIC_REPORT_NOT_NATIVE_GAME_ACCEPTANCE",
 "registry_sha256":SHA(REG),"predecessor_handoff_sha256":SHA(PREV),
 "semantic_delta_sha256":dsha,"static_verification_sha256":sources["STATIC_VERIFICATION.json"],
 "source_evidence_sha256":sources,"portfolio":rows,"execution":execution,
 "preservation":delta["preservation"],
 "admission":{"ORCH_K003_K004":"NOT_GRANTED_OR_RECHECKED",
   "runtime_capture":"NONE","new_native_worker_or_lease":False},
 "reproduce":{"command":"python -B verify_cont20_static.py",
   "expected":r["status"],"deterministic_create_only_or_same_bytes":True,
   "not_native_game_rehydration_contract":True}
}
hsha=emit("READ_ONLY_HANDOFF.json",handoff)
summary="""# OpenRemaster — CONT20 (2026-10-09)

SOURCE-STATIC PASS only, NOT native gameplay, capture or fidelity acceptance.
23/23 portfolio rows carried forward under operation
OR-PORTFOLIO-DAILY-READ-20261009-42037bc7fd56.

## MDK1 — group-indexed mutable triangle state

Original MDK95.EXE routine 0x40A704 changes original triangle+0x20
flags by matching the high-byte group ID. Supported actions 0..5
set/clear 0x30, 0x10 or 0x20. An unsigned action above5 uses
the default CLEAR0x30; group0 and group>255 are rejected.

Original LEVEL3 MTO contains 7205 triangles: 6161 group0, 1044
in groups1..14. Group7 has 186 original source triangles with pinned
source file offsets, F3s and SHA-256 in MDK_GROUP7_SOURCE_MEMBERS.json.
Source flags0x10/0x20 are initially clear. The real renderer0x409860
skips normal triangle processing for bit0x10 set. Live state changes,
camera and actual pixel output remain unverified.

## Stonekeep — exact serialized h415 tile bit0x02

SHA-pinned LEVEL01A.SAV grid=26x29 at21-byte stride, offset11.
At (23,3) cell byte0=0x01, static byte2=0x8B,
handler=415, file offset14081. Original action0 calls selector1
map getter and checks byte0&0x02; under unchanged tile and position,
branch0x3D383 (level status/audio) is selected, not rectangle path
0x3D3EE. Original level15 callback0x4F861 is RET.
Dynamic tile mutation, audio helper0x81D73 and input event8
interleaving remain UNKNOWN, no promotion to gameplay PASS.

## Ultima8 — name alias array

Original NE130 manages DS:8C0A far-name-pointer array: allocation,
zeroing, indexed slot clear, free/null. NE126 writes a far pointer
to USECODE shape*13+4 name into this array. The reviewed stores do not
directly modify USECODE record+0..3 flags. Original source shape347
CLRWATER flags0x40 fail mask0x000F8000. No whole-game guarantee of
loaded table immutability or real Map5 instance population.

## Validation/custody

14 source regions;70 original opcode checks.
35 pure MDK models,9 Stonekeep tile models,4 Ultima8 offset models.
Native original instruction tests, game runtime, heavy jobs, builds
and captures: ZERO. Original corpus, project worktrees, portfolio
registry, shared journal, tickets, leases, writers unchanged.
Azrael Retail PAUSED; Demo CLOSED; ROTH WARM_COMPLETION;
Framework Phase1 FROZEN and native production admission BLOCKED.
"""
sp=HERE/"CONT20_SUMMARY.md"
if sp.exists():assert sp.read_text(encoding="utf-8")==summary
else:
    with sp.open("x",encoding="utf-8") as f:f.write(summary)
names=("verify_cont20_static.py","MDK_GROUP7_VISIBILITY_CONTRACT.json",
       "MDK_GROUP7_SOURCE_MEMBERS.json","STONEKEEP_H415_SERIALIZED_TILE_AND_BRANCH.json",
       "U8_USECODE_NAME_POINTER_ARRAY_BOUND.json","STATIC_VERIFICATION.json",
       "complete_cont20_handoff.py","SEMANTIC_DELTA.json",
       "READ_ONLY_HANDOFF.json","CONT20_SUMMARY.md")
assert all((HERE/n).exists() for n in names)
mp=HERE/"manifest.json";manifest=read("manifest.json")
manifest.update(operation_id=prior["operation_id"],iteration_id="CONT20",
  predecessor_handoff_sha256=SHA(PREV),
  artifact_role="READ_ONLY_SOURCE_STATIC_REPORT_NOT_NATIVE_ACCEPTANCE",
  outputs=[{"file":name,"sha256":SHA(HERE/name),
            "role":"ORIGINAL_SOURCE_STATIC_EVIDENCE_OR_REPORT"} for name in names])
mp.write_text(json.dumps(manifest,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
assert all(SHA(HERE/item["file"])==item["sha256"] for item in manifest["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text())["portfolio"])==23
print(json.dumps({
 "result":"PASS_CONT20_REPORT_MANIFEST_23_LANES_SOURCE_STATIC_ONLY",
 "run_id":delta["run_id"],"portfolio":23,"source_regions":14,
 "original_opcode_checks":70,"pure_models":{"MDK":35,"Stonekeep":9,"Ultima8":4},
 "original_game_runtime_tests":0,"artifacts":len(manifest["outputs"]),
 "sha256":{name:SHA(HERE/name) for name in
   ("STATIC_VERIFICATION.json","SEMANTIC_DELTA.json",
    "READ_ONLY_HANDOFF.json","CONT20_SUMMARY.md","manifest.json")}
},sort_keys=True))
