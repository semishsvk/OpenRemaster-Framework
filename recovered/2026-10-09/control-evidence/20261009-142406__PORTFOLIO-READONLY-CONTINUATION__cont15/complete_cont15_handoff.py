"""Complete isolated read-only CONT15 handoff, with exact 23-lane carry-forward.

No mutation outside this new report directory. Static source tests do not
create native game/runtime/fidelity or production acceptance.
"""
from pathlib import Path
import hashlib,json,copy,datetime,sys,capstone
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-140226__PORTFOLIO-READONLY-CONTINUATION__cont14/READ_ONLY_HANDOFF.json"
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
SHA=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def load(n):return json.loads((HERE/n).read_text(encoding="utf-8"))
prior=json.loads(PREV.read_text(encoding="utf-8-sig"))
r=load("STATIC_VERIFICATION.json")
u8=load("U8_USECODE_FLX_NEGATIVE.json")
mdk=load("MDK_RASTER_CALLBACK_DISPATCH.json")
sk=load("STONEKEEP_ACTION0_LEVEL_CALLBACKS.json")
assert SHA(PREV)=="855adba6d4aa3e70b2567741d416a872f2055e082d2dc3fc7f22c68c7c0521f7"
assert SHA(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
assert len(prior["portfolio"])==23 and len({p["project"] for p in prior["portfolio"]})==23
assert prior["operation_id"]==r["operation_id"]
assert r["status"]=="PASS_SOURCE_STATIC_AND_GROUNDED_RESOURCE_NEGATIVE_ONLY"
assert r["source_byte_and_disasm_check_count"]==11
assert r["source_opcode_check_count"]==53
assert r["usecode_archive_entries"]==1433 and r["usecode_metadata_records"]==1431
assert r["usecode_positive_mask_control_count"]==103
assert r["special_class_source_ir_count"]==2360 and r["special_class_capability_positive_count_under_base_usecode"]==0
assert r["mdk_raster_callback_pointers"]==24 and r["stonekeep_global_level_callback_targets"]==22
assert u8["entry1"]["glob218_shape347"]["flags"]==0x40
assert u8["entry1"]["glob218_shape347"]["mask_result"]==0
assert u8["entry1"]["positive_control"]["mask_result"]!=0
assert sk["store_count"]==22 and len(sk["direct_global_level_callback_stores"])==22
assert not r["game_runtime_executed"] and not r["fidelity_or_release_verified"]
assert r["original_game_machine_instructions_executed"]==0

focus={
 "OpenUltima8":{
  "status":"USECODE_SHAPE347_DEFAULT_CAPABILITY_GATE_STATIC_FALSIFICATION; LIVE_TABLE_MUTATION_AND_FIDELITY_HOLD",
  "progress":"Discovered source USECODE/EUSECODE.FLX entry1 1431*13 byte records; original loader NE126:0xaf4 copies member1 into DS:0x88f6 via resource vtable. Shape347 CLRWATER source flags0x40 fail requested capability mask0x000F8000, including all2360 potential Map5 bit7 children under unmodified table; negative boundary, not live scene verdict.",
  "next":"Pin whether USECODE entry1 is modified at runtime after NE126:0xaf4, then collect bounded original handle/table readback and paired GLOB218 shape347 vs shape128 status under approved runtime.",
  "evidence_class":"NEW_SOURCE_RESOURCE_NEGATIVE_WITH_UNVERIFIED_NATIVE_MEMORY"
 },
 "OpenMDK1":{
  "status":"BOTH_12_SLOT_RASTER_DISPATCH_TABLES_STATICALLY_BOUND; SELECTED_PROFILE_AND_PIXELS_HOLD",
  "progress":"The two48-byte CPU profile buffers consist of12 original executable addresses each. Raster path0x46ded4 chooses slots0..7 by two mode bits and optional+4; indirect call EBX occurs four times. Path0x46e544 selects slots8..11 and calls via[EBP-0x28] at0x46e886.",
  "next":"Trace one clipped LEVEL3 original triangle to selected live CPU table/index, check fan UV and source signed-f3, then original runtime frame/pixel acceptance.",
  "evidence_class":"NEW_DISPATCH_SOURCE_OPCODE_FUNCTION_POINTER_CONTRACT_NOT_PIXEL_FIDELITY"
 },
 "OpenStonekeep":{
  "status":"H415_ACTION0_INDIRECT_LEVEL_CALLBACK_REACHABLE_STATICALLY; TRANSITIVE_REENTRY_UNVERIFIED",
  "progress":"h415 action0 fallback0x4fc9e→0x6a230→0x6a183→0xac4aa selector0→0xac68c→0x3d4f5 calls level callback pointer0x1b9ddc. Original LE relocation scan found22 unique direct assigned level callback targets and one indirect call; none assigned directly to staging0xa2ba6.",
  "next":"Independently validate exact level callback active at h415 level15 and whether its transitive calls can stage h415 action2/3 before event8 service; retain queue-full/reentry negative fixtures.",
  "evidence_class":"NEW_ORIGINAL_LEVEL_CALLBACK_STATIC_XREFS_NOT_REENTRY_PROOF"
 }
}
rows=copy.deepcopy(prior["portfolio"])
baseline={x["project"]:x["lane"] for x in rows}
for x in rows:
    k=x["project"]
    if k in focus:x.update(focus[k])
    elif k=="OpenRemasterOrchestrator":
        x.update(status="STATIC_REPORT_ONLY_NATIVE_PRODUCTION_NOT_ADMITTED",
                 progress="Completed isolated CONT15 source-static USECODE negative, MDK dispatch, Stonekeep level callback mapping; preserved23 lanes; no native jobs",
                 next="Use original evidence-based per-game gates, no duplicate writer or unrelated warm dispatch",
                 evidence_class="CONTROL_PLANE_REPORT_ONLY")
    else:x["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED_OR_DISPATCHED"
assert len(rows)==23 and baseline=={x["project"]:x["lane"] for x in rows}
assert {x["project"] for x in rows if x["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(x for x in rows if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in rows if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in rows if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def emit_json(name,obj):
    data=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    p=HERE/name
    with p.open("xb") as f:f.write(data)
    return SHA(p)

delta={
 "schema":"OpenRemaster.ReadOnlySemanticDelta.v15",
 "operation_id":prior["operation_id"],"iteration_id":"CONT15",
 "run_id":"20261009-142406__PORTFOLIO-READONLY-CONTINUATION__cont15",
 "predecessor_sha256":SHA(PREV),"registry_sha256":SHA(REG),
 "focus":focus,
 "source_receipts":{
     "U8_USECODE_FLX_NEGATIVE.json":SHA(HERE/"U8_USECODE_FLX_NEGATIVE.json"),
     "MDK_RASTER_CALLBACK_DISPATCH.json":SHA(HERE/"MDK_RASTER_CALLBACK_DISPATCH.json"),
     "STONEKEEP_ACTION0_LEVEL_CALLBACKS.json":SHA(HERE/"STONEKEEP_ACTION0_LEVEL_CALLBACKS.json"),
     "STATIC_VERIFICATION.json":SHA(HERE/"STATIC_VERIFICATION.json")},
 "execution":{"native_game_instruction_tests":0,"game_runtime":0,"builds":0,"captures":0,"heavy_jobs":0,"new_lease":0,
              "source_or_game_worktree_write":0,"writer_ticket_changes":0,"shared_journal_changed":False,"production_admission":False},
 "preservation":{"portfolio":23,"azrael_retail":"PAUSED_NOT_REPOLLED","azrael_demo":"CLOSED_ARCHIVED",
                 "roth":"WARM_COMPLETION_UNTOUCHED","framework_phase1":"FROZEN_UNCHANGED"},
 "status":"SOURCE_STATIC_NEGATIVE_AND_DISPATCH_CONTRACTS_VERIFIED_NO_NATIVE_FIDELITY_PROMOTION"
}
ds=emit_json("SEMANTIC_DELTA.json",delta)
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v15",
 "operation_id":prior["operation_id"],"iteration_id":"CONT15","run_id":delta["run_id"],
 "status":delta["status"],"artifact_role":"PERSISTENT_READ_ONLY_STATIC_REPORT_NOT_GAME_ACCEPTANCE",
 "predecessor_handoff_sha256":SHA(PREV),"registry_sha256":SHA(REG),
 "semantic_delta_sha256":ds,
 "static_verification_sha256":SHA(HERE/"STATIC_VERIFICATION.json"),
 "portfolio":rows,"execution":delta["execution"],"preservation":delta["preservation"],
 "inputs":r["source_pins"],
 "evidence_summary":{
   "source_disassembly_regions":11,"source_opcode_checks":53,
   "usecode_archive_entries":1433,"usecode_capability_records":1431,
   "usecode_mask_positive_control_shapes":103,"shape347_default_mask_result":0,
   "Map5_potential_special_children":2360,"actual_live_instances":"UNKNOWN",
   "MDK_raster_function_pointer_slots":24,
   "Stonekeep_level_callback_sources":22
 },
 "admission":{"ORCH_K003_K004":"NOT_RECHECKED_OR_GRANTED","runtime_original_authority":"NOT_PROVIDED",
              "original_source_read_only_observed_by_this_iteration":"CONTENT_HASH_PINNED_NO_WRITES",
              "new_writer_or_fencing_lease":False},
 "reproduction":{
   "command":"python -B verify_cont15_static.py",
   "expected_status":r["status"],
   "idempotence":"Source report outputs require byte equality; cannot overwrite divergent output",
   "not_full_rehydration_contract":True,
   "capstone":capstone.__version__,"python":sys.version.split()[0],
   "verifier_sha256":SHA(HERE/"verify_cont15_static.py")},
 "recorded_at_utc":now
}
hs=emit_json("READ_ONLY_HANDOFF.json",handoff)
summary=f"""# OpenRemaster CONT15 — 9. október 2026

**Scope: source-static semantics, not original game execution or fidelity.**
Run: `{delta['run_id']}`  
Operation: `{delta['operation_id']}`
23/23 portfolio records carried forward, 3 focus read-only lanes.

## OpenUltima8 — grounded resource-level negative
Original NE126:0xAF4 reads source token `usecode` and, through a
resource object's virtual members +0x14 and +0x1C, allocates a table
to DS:0x88F6. The original `USECODE/EUSECODE.FLX` has **1433
entries**, with **entry1 length 18603 = 1431 x 13 bytes**.

The source metadata record for **shape347, CLRWATER** has flags
`0x00000040`. The source-gate mask passed from NE28:0x2577
to NE126:0xBF7 is `0x000F8000`.
Their bitwise AND is **ZERO**.
Of all 1431 usecode records, **103** have a nonzero mask result,
demonstrating valid positive controls.

All **2360** original Map5 *potential* GLOB shape347 children have
this source-default negative gate. It falsifies the assumption that
TYPEFLAG highbit alone implies downstream secondary allocation.
**Conditional:** the runtime usecode table must equal this original
source record at that moment. This audit has no live memory readback
and does not exclude mutations by runtime script/helper code.
The existing generic item construction and earlier lifecycle effects
are separate and may still occur.

**Next:** independently establish loaded table content and mutation/
reallocation rules, then trace the authentic GLOB218 paired source
on admitted original runtime.

## OpenMDK1 — original raster function pointer dispatch
Each profile is 48 bytes and holds **12 runnable code addresses**.
Original CPU detector selects A or B; source code copies the table to
0x54DC00. Dynamic index at 0x46DED4 uses
`(vertexMode & 3) | (4 if global0x5414B8 else 0)` for slots0..7.
Actual calls via EBX: 0x46E097/0x46E250/0x46E3E0/0x46E4D5.
A second raster path indexes slot8..11 at 0x46E544 and calls via
[EBP-0x28] at 0x46E886. All 24 slot targets decode as source code.

**Next:** select an authentic LEVEL3 clipped triangle, recover live
profile + slot + signed-f3 and verify original frame/pixel output.

## OpenStonekeep — action0 still reaches a second callback
h415 action0 calls 0x6A230 then 0x6A183, which passes selector0
to 0xAC4AA. The direct action-specific path exits via 0xAC68C,
which calls 0x3D4F5. That routine dispatches a **different callback**
from 0x1B9DDC (global level callback).
Original LE relocations identify **22 unique writer targets**
and one indirect caller. None of the assigned targets is directly
h415 staged-transition function0xA2BA6.
Indirect effects beyond each level handler are **not verified**.

**Next:** bind the actual level-15 handler and trace if a second
action2/3 staged transition is reachable before the event8 loader.

## Validation and admission
- Whole-source SHA pins: MDK95.EXE, SK.EXE, U8.EXE, TYPEFLAG.DAT,
  EUSECODE.FLX, Map5 SourceIR, predecessor handoff, registry.
- Source disassembly regions: **11**; opcode checks: **53**.
- USECODE record count: **1431**; source-default mask positive records **103**.
- MDK raster callback function pointers **24**.
- Stonekeep original global level callback targets **22**.
- Original game instructions/runtime/builds/GPU captures/heavy slots **0**.
- No modifications outside the new report directory.
- Azrael Retail **PAUSED**, Demo **CLOSED**, ROTH **WARM_COMPLETION**,
  Phase 1 Framework **FROZEN**, native production admission unchanged.

**Verdict:** SOURCE_STATIC_NEGATIVE_AND_DISPATCH_PASS, not playable,
original-runtime, fidelity or release acceptance.
"""
sp=HERE/"CONT15_SUMMARY.md"
with sp.open("x",encoding="utf-8") as f:f.write(summary)
manifest=HERE/"manifest.json"
m=json.loads(manifest.read_text(encoding="utf-8-sig"))
names=("verify_cont15_static.py","complete_cont15_handoff.py","U8_USECODE_FLX_NEGATIVE.json",
       "MDK_RASTER_CALLBACK_DISPATCH.json","STONEKEEP_ACTION0_LEVEL_CALLBACKS.json",
       "STATIC_VERIFICATION.json","SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT15_SUMMARY.md")
m.update(operation_id=prior["operation_id"],iteration_id="CONT15",
         artifact_role="ORIGINAL_SOURCE_STATIC_REPORT_ONLY_NOT_PRODUCTION_OR_FIDELITY",
         predecessor_handoff_sha256=SHA(PREV),
         outputs=[{"file":name,"sha256":SHA(HERE/name),"role":"STATIC_SOURCE_EVIDENCE_OR_REPORT"} for name in names])
manifest.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
assert all(SHA(HERE/e["file"])==e["sha256"] for e in m["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text())["portfolio"])==23
assert SHA(PREV)==delta["predecessor_sha256"] and SHA(REG)==delta["registry_sha256"]
print(json.dumps({
 "status":"PASS_REPORT_MANIFEST_23_LANES_STATIC_ONLY",
 "run_id":delta["run_id"],"portfolio":23,"source_regions":11,
 "opcode_checks":53,"EUSECODE_entry1_records":1431,
 "Map5_shape347_default_mask_positive":0,
 "raster_slots":24,"stonekeep_level_callbacks":22,
 "game_runtime_tests":0,
 "artifact_sha256":{name:SHA(HERE/name) for name in
  ("SEMANTIC_DELTA.json","STATIC_VERIFICATION.json","READ_ONLY_HANDOFF.json","CONT15_SUMMARY.md","manifest.json")}
},sort_keys=True))
