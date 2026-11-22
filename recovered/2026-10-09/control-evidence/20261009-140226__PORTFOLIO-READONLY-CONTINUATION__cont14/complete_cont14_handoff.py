"""Finalize CONT14 unique report-only handoff. Preserves all 23 portfolio lanes."""
from pathlib import Path
import json,hashlib,copy,datetime,sys
import capstone
BASE=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=BASE/"output/projects/OpenRemasterOrchestrator/reports/20261009-132559__PORTFOLIO-READONLY-CONTINUATION__cont13/READ_ONLY_HANDOFF.json"
REG=BASE/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):
    return json.loads((HERE/name).read_text(encoding="utf-8"))
old=json.loads(PREV.read_text(encoding="utf-8-sig"))
result=read("STATIC_VERIFICATION.json")
mdk=read("MDK1_RENDER_PROFILE_CONTRACT.json")
stone=read("STONEKEEP_H415_CALLBACK_CONTRACT.json")
u8=read("U8_SPECIAL_CALLBACK_GATE.json")
assert sha(PREV)=="cc0240f6b2a2948d30a8ffa7fc3b74835a98dc15bb6fc57b71b4fad02cd5f302"
assert sha(REG)=="42037bc7fd5699ba54aaae4b10de1bd13607e8e2b52fb2042140abcc6bfb378a"
assert result["status"]=="PASS_ORIGINAL_SOURCE_OPCODE_RELOCATIONS_AND_PURE_CONTRACT_MODELS"
assert old["operation_id"]==result["operation_id"]
assert len(old["portfolio"])==23
assert result["region_count"]==22
assert result["opcode_count"]==76
assert len(result["NE_relocations"])==6
assert result["model_fixtures"]=={"U8":128,"MDK1":9,"Stonekeep":4}
assert stone["pointer_xref_count"]==79
assert stone["pointer_access_categories"]=={
  "direct_indirect_call":74,"direct_immediate_store":1,"direct_eax_store":1,"address_of_pointer":3}
assert u8["positive_model_cases"]==2
assert len(u8["representatives"])==4
assert result["original_machine_instructions_executed"]==0
assert not result["native_runtime_or_capture_executed"]
assert not result["game_fidelity_verified"]

focus={
 "OpenUltima8":{
  "status":"SPECIAL_SHAPE347_CAPABILITY_AND_RECORD_ALLOCATION_STATIC_CONTRACT; LIVE_FIDELITY_BLOCKED",
  "progress":"Resolved NE126:0xbf7 gated by DS8906, shape-indexed 13-byte table DS88F6, 0x000F8000 mask and conditional NE132:0x137 0x116-byte secondary-record allocation. 128 pure cases; exact Map5 GLOB218 pairs have runtime IDs unbound.",
  "next":"Validate GLOB218 shape347 versus shape128 original runtime handles and shape347 capability-record contents, then observe additional allocation and sector/grid epochs under admitted, independently captured replay.",
  "evidence_class":"NEW_SOURCE_STATIC_AND_PURE_CONDITIONAL_NO_ORIGINAL_RUNTIME"
 },
 "OpenStonekeep":{
  "status":"H415_CURRENT_CELL_CALLBACK_ACTION0_BOUND_DIRECT_RESTAGING_NOT_SHOWN",
  "progress":"Confirmed handler415 target0x4f983; poll callback sends action0 and original action gate routes it away from direct action2/3 staging path. Scoped 79 relocated pointer refs: 74 indirect calls, 2 direct stores, 3 address-of uses; indirect helper side effects remain unverified.",
  "next":"Read-only trace h415 action0 helpers and dynamic input routing to determine if action2/3 could run before queued event8; distinguish no-direct-stage from no-transitive-stage and retain queue-full negative fixtures.",
  "evidence_class":"NEW_SOURCE_STATIC_DIRECT_ACTION_GATE_NOT_RUNTIME_EVENT_REPLAY"
 },
 "OpenMDK1":{
  "status":"CPU_DETECTOR_TO_A_B_RASTER_PROFILE_SELECTION_STATIC_BOUND; LIVE_SELECTION_FIDELITY_BLOCKED",
  "progress":"Closed normal-return EDX preservation through CPU helper0x425310 and external wrapper0x408f3c→0x47f47f incl error routine0x481758. Detector with AH cleared equals6 selects 48-byte profile at0x49bcb4; all other values select0x49bce4. Both profile bytes are source SHA-pinned.",
  "next":"Capture original detector value, selected profile and clipped LEVEL3 triangle fan vertex/UV/material/pixel replay under approved worker and independent original runtime authority.",
  "evidence_class":"NEW_STATIC_SOURCE_CPU_PROFILE_MECHANISM_NOT_OBSERVED_LIVE"
 }
}
rows=copy.deepcopy(old["portfolio"])
baseline={r["project"]:r["lane"] for r in rows}
for row in rows:
    project=row["project"]
    if project in focus:
        row.update(focus[project])
    elif project=="OpenRemasterOrchestrator":
        row.update({
          "status":"REPORT_ONLY_PRODUCTION_ADMISSION_BLOCKED",
          "progress":"CONT14 isolated source-static models and evidence manifest; 23/23 portfolios preserved without lease/job/writer mutations",
          "next":"Continue game-driven narrow blockers only; do not register a production job or duplicate writer",
          "evidence_class":"CONTROL_PLANE_REPORT_ONLY_NOT_ACCEPTANCE"
        })
    else:
        row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED"
assert len(rows)==23 and len({r["project"] for r in rows})==23
assert {r["project"]:r["lane"] for r in rows}==baseline
assert {r["project"] for r in rows if r["lane"]=="FOCUS_READ_ONLY"}==set(focus)
assert next(r for r in rows if r["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(r for r in rows if r["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(r for r in rows if r["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"

delta={
  "schema":"OpenRemaster.ReadOnlySemanticDelta.v14",
  "operation_id":old["operation_id"],"iteration_id":"CONT14",
  "run_id":"20261009-140226__PORTFOLIO-READONLY-CONTINUATION__cont14",
  "predecessor_handoff_sha256":sha(PREV),"registry_sha256":sha(REG),
  "focus":focus,
  "new_replay_fidelity":False,
  "source_static_sha256":sha(HERE/"STATIC_VERIFICATION.json"),
  "paired_U8_source_fixture":"fixed:m5:r2378:g218:s0 shape347 vs fixed:m5:r2378:g218:s12 shape128",
  "MDK1_profiles":{"cpu_AH_cleared_equals_6":"0x49bcb4","other":"0x49bce4",
                   "profile_raw_sha256":{x["source_address"]:x["sha256"] for x in mdk["table_pins"]}},
  "Stonekeep_h415":{"handler_target":"0x4f983","input_callback_action":0,"direct_action0_staging":False,
                    "indirect_reentry":"UNVERIFIED"},
  "execution":{"original_game_instruction_tests":0,"native_game_runtime":0,"native_heavy_jobs":0,"builds":0,"captures":0,
               "source_or_project_worktree_writes":0,"new_native_admission":False,"shared_execution_journal_mutated":False},
  "preservation":{"portfolio_entries":23,"azrael_retail":"PAUSED_NO_REPOLL","azrael_demo":"CLOSED_ARCHIVED",
                  "roth":"WARM_COMPLETION_NOT_DISPATCHED","framework_phase1":"FROZEN",
                  "existing_tickets_writers_leases":"NOT_MUTATED"},
  "evidence_scope":"New original-source static and pure-model contracts, not a native game acceptance or fidelity PASS."
}
now=(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text(encoding="utf-8"))["recorded_at_utc"] if (HERE/"READ_ONLY_HANDOFF.json").exists() else datetime.datetime.now(datetime.timezone.utc).isoformat())
handoff={
  "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v14",
  "operation_id":old["operation_id"],
  "iteration_id":"CONT14",
  "run_id":delta["run_id"],
  "status":"NEW_SOURCE_STATIC_MECHANISMS_VERIFIED_RUNTIME_FIDELITY_HOLD",
  "artifact_role":"ISOLATED_REPORT_NOT_PRODUCTION_CHECKPOINT",
  "previous_handoff_sha256":sha(PREV),
  "registry_sha256":sha(REG),
  "portfolio":rows,
  "evidence":{
    "source_exe_sha256":{k:result["source_sha256"][k] for k in ("MDK1","Stonekeep","Ultima8")},
    "source_regions_checked":22,"source_opcode_checks":76,"original_NE_relocations_checked":6,
    "stonekeep_pointer_references_checked":79,
    "pure_model_cases":result["model_fixtures"],
    "new_original_game_instructions_executed":0,
    "new_native_or_runtime_fidelity_tests":0,
    "static_contracts_sha256":{
       name:sha(HERE/name)
       for name in ("STATIC_VERIFICATION.json","MDK1_RENDER_PROFILE_CONTRACT.json",
                    "STONEKEEP_H415_CALLBACK_CONTRACT.json","U8_SPECIAL_CALLBACK_GATE.json")}
  },
  "execution":delta["execution"],
  "preservation":delta["preservation"],
  "policy":{
    "native_worker_commissioning":"NOT_RECHECKED_OR_GRANTED",
    "resource_leases":"NOT_REQUESTED_OR_CREATED",
    "original_runtime_capture_authority":"NOT_INVOLVED",
    "fidelity_acceptance":"NOT_GRANTED",
    "originals":"SHA_PINNED_AND_UNMODIFIED",
    "report_writer_scope":"only this fresh CONT14 reports directory"
  },
  "rehydration_note":{
    "recipe":"python -B verify_cont14_static.py",
    "expected":result["status"],
    "idempotent_report_outputs":True,
    "not_a_full_native_game_rehydration_contract":True,
    "python_version":sys.version.split()[0],
    "capstone_version":capstone.__version__,
    "verifier_sha256":sha(HERE/"verify_cont14_static.py")
  },
  "recorded_at_utc":now
}

summary=f"""# OpenRemaster — CONT14 | 9. októbra 2026

**Scope: original source-static mechanisms, pure contract fixtures; NOT game runtime or fidelity PASS.**  
Operation ID: {delta['operation_id']}  
Run: {delta['run_id']}  
Portfolio: **23/23**, lanes unchanged.

## OpenUltima8 — shape347 callback now has a concrete allocation gate

The original path NE28:0x2577 → NE126:0xBF7 is not enabled by the
TYPEFLAG high bit alone. It requires a valid original activation path,
a handle outside the 1..255 special-ID range, zero DS:0x8906,
non-null table DS:0x88F6, and a matching bit in the shape-indexed
**13-byte** record. The call site supplies the combined mask
**0x000F8000**.

On the matching path NE126:0xCED receives a null record pointer and
attempts the **0x116-byte** allocation through NE132:0x137 before
initialization of the record. These are source-level instructions and
conditional model paths; the live pointer, table bits, callback count,
original execution and any resulting in-world object remain UNKNOWN.

Authentic pair: fixed:m5:r2378:g218:s0 (shape347, bit7=1) versus
fixed:m5:r2378:g218:s12 (shape128, bit7=0). Corresponding pairs
also exist in r2379. Both belong to the same GLOB218 source family.
The 128 pure gate cases include **2 conditionally eligible cases**,
but these are not observations of real game execution.

**Next:** capture actual original handles, table contents, callback
effects and post-callback sector/grid status under approved admission.

## OpenMDK1 — CPU-profile selector and source tables

Normal-return trace:
- 0x401B40 sets EDX=1.
- CPU detector 0x425310 and 0x408F3C→0x47F47F preserve EDX,
  with 0x481758 restoring it on normal error-handler return.
- 0x401B6D reloads detector result; 0x401B72 zeroes AH.
- 0x401B74 compares normalized result to 6.
- For 6, 0x401B7D transfers EDX=1 into EAX.
- Otherwise 0x401DA4 sets EAX=0.
- 0x46DA6C copies the 48-byte profile from the respective original
  source address into 0x54DC00.

Source table A 0x49BCB4: SHA-256
{mdk['table_pins'][0]['sha256']}

Source table B 0x49BCE4: SHA-256
{mdk['table_pins'][1]['sha256']}

Nine pure detector-result cases passed. **The live CPU detector result
and selected frame profile remain unobserved.**

## OpenStonekeep — input callback pointer and h415 direct gate

The original h415 relocation resolves to entry **0x4F983**.
The input pump at 0x32D45 passes **EAX=0** to the callback pointer
0x1B9DF4. Handler h415 checks the action at 0x4F9B1:
actions 0 and 1 branch away from the direct action2/3 path.

Original LE source pointer xrefs: **79** occurrences:
74 indirect calls, 2 direct stores and 3 address-of uses.
The pointer is set at 0x44F10 from dispatch table 0xF16A and
is updated by 0x3DFCC using the handler ID in the current map cell.
No direct action0 h415 staging was observed in the bounded entry path.
Transitive helper effects and any later input action2/3 remain
UNVERIFIED. Do not conclude global no-reentry or a proven softlock.

**Next:** trace h415 action0 helper side effects and input-driven
action2/3 reachability, then independently replay queue/full and
staged-payload generation before E.16 promotion.

## Validation and custody

- SHA pins: original MDK95.EXE, SK.EXE, U8.EXE, TYPEFLAG.DAT,
  Map5 SourceIR, registry and predecessor handoff.
- 22 original-byte disassembly regions and 76 opcode checks.
- 6 far NE relocation target checks.
- 79 Stonekeep callback pointer operand sources enumerated.
- 128 U8, 9 MDK1, and 4 Stonekeep **pure models**, not game tests.
- Native game instruction execution: **0**.
- Heavy jobs, runtime, builds, captures, game worktree writes: **0**.
- Only new CONT14 reports directory mutated; shared journal, tickets,
  writers, leases, registry, Phase1 frozen baseline all unchanged.
- Azrael Retail PAUSED, Demo CLOSED, ROTH WARM_COMPLETION.

Verdict: **PASS_SOURCE_STATIC**. No playable/fidelity/release PASS.
"""
def emit(name,obj):
    p=HERE/name
    blob=(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode("utf-8")
    if p.exists():assert p.read_bytes()==blob,("OUTPUT_CONFLICT",name)
    else:
        with p.open("xb") as f:f.write(blob)
    return sha(p)
delta_sha=emit("SEMANTIC_DELTA.json",delta)
handoff["evidence"]["semantic_delta_sha256"]=delta_sha
hp_sha=emit("READ_ONLY_HANDOFF.json",handoff)
sp=HERE/"CONT14_SUMMARY.md"
if sp.exists():assert sp.read_text(encoding="utf-8")==summary
else:
    with sp.open("x",encoding="utf-8") as f:f.write(summary)
mp=HERE/"manifest.json"
m=json.loads(mp.read_text(encoding="utf-8-sig"))
m.update(
  operation_id=delta["operation_id"],iteration_id="CONT14",
  artifact_role="ORIGINAL_SOURCE_STATIC_REPORT_ONLY_NOT_ACCEPTANCE_OR_NATIVE_ADMISSION",
  predecessor_handoff_sha256=delta["predecessor_handoff_sha256"],
  outputs=[{"file":name,"sha256":sha(HERE/name),"role":"STATIC_SOURCE_CONTRACT_OR_REPORT_ONLY"} for name in
  ("verify_cont14_static.py","complete_cont14_handoff.py",
   "MDK1_RENDER_PROFILE_CONTRACT.json","STONEKEEP_H415_CALLBACK_CONTRACT.json",
   "U8_SPECIAL_CALLBACK_GATE.json","STATIC_VERIFICATION.json",
   "SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT14_SUMMARY.md")]
)
mp.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
assert all(sha(HERE/item["file"])==item["sha256"] for item in m["outputs"])
assert len(json.loads((HERE/"READ_ONLY_HANDOFF.json").read_text())["portfolio"])==23
assert sha(REG)==delta["registry_sha256"] and sha(PREV)==delta["predecessor_handoff_sha256"]
print(json.dumps({
 "status":"PASS_STATIC_REPORT_MANIFEST_AND_23_PORTFOLIO_ONLY",
 "portfolio_count":23,"source_region_checks":22,"opcode_checks":76,
 "ne_relocations":6,"stonekeep_pointer_xrefs":79,
 "pure_fixture_cases":result["model_fixtures"],"game_runtime_tests":0,
 "run_id":delta["run_id"],
 "files":{f:sha(HERE/f) for f in (
      "STATIC_VERIFICATION.json","SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json",
      "CONT14_SUMMARY.md","manifest.json")}
},sort_keys=True))
