"""Finalize isolated CONT11 report, preserving all 23 portfolio records.

Mutates only the newly allocated reports/CONT11 directory.
"""
import json
import hashlib
import sys
import datetime
import copy
from pathlib import Path
import capstone
BASE=Path(r"F:\Remaster Framework")
RUN=Path(__file__).resolve().parent
PRIOR=BASE/"output/projects/OpenRemasterOrchestrator/reports/20261009-120436__PORTFOLIO-READONLY-CONTINUATION__cont10/READ_ONLY_HANDOFF.json"
REG=BASE/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
def fp(path):return hashlib.sha256(path.read_bytes()).hexdigest()
d=json.loads((RUN/"SEMANTIC_DELTA.json").read_text(encoding="utf-8"))
v=json.loads((RUN/"STATIC_VALIDATION.json").read_text(encoding="utf-8"))
prev=json.loads(PRIOR.read_text(encoding="utf-8-sig"))
assert fp(PRIOR)==d["previous_handoff_sha256"]
assert fp(REG)==d["registry_sha256"]
assert len(prev["portfolio"])==23 and len({e["project"] for e in prev["portfolio"]})==23
assert v["status"]=="PASS_STATIC_BYTE_OPCODE_RELOCATION_AND_NEGATIVE_CONTRACT_FIXTURES_ONLY"
assert v["semantic_delta_sha256"]==fp(RUN/"SEMANTIC_DELTA.json")
assert v["source_regions_checked"]==21 and v["original_instruction_and_fixture_checks"]==115 and v["ne_relocations_checked"]==10
assert v["original_game_instructions_executed"]==0 and not v["fidelity_verified"]
assert d["iteration_id"]=="CONT11" and d["operation_id"]==prev["operation_id"]
assert set(d["focus"])=={"OpenMDK1","OpenStonekeep","OpenUltima8"}
assert all(x==0 for x in (d["execution"]["source_writes"],d["execution"]["project_code_changes"],
 d["execution"]["game_instruction_or_emulator_tests"],d["execution"]["heavy_jobs"],
 d["execution"]["production_runtime"],d["execution"]["builds"],d["execution"]["captures"]))

portfolio=copy.deepcopy(prev["portfolio"])
for entry in portfolio:
    name=entry["project"]
    if name in d["focus"]:
        f=d["focus"][name]
        entry.update(
            status="BLOCKED_RUNTIME_FIDELITY",
            progress=f["delta"],
            next=f["next"],
            new_evidence_class="STATIC_ORIGINAL_SOURCE_VERIFIED_NOT_RUNTIME"
        )
    elif name=="OpenRemasterOrchestrator":
        entry.update(
            progress="CONT11 source-static verification and report-only handoff; no production/native admission",
            next="Reuse same operation identity; no duplicate writer or unrelated warm dispatch",
            new_evidence_class="CONTROL_PLANE_REPORT_ONLY"
        )
    else:
        entry["new_evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED_OR_EXECUTED"
assert len(portfolio)==23 and len({e["project"] for e in portfolio})==23
assert {x["project"]:x["lane"] for x in portfolio}=={x["project"]:x["lane"] for x in prev["portfolio"]}
assert next(x for x in portfolio if x["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(x for x in portfolio if x["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(x for x in portfolio if x["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt={
 "schema":"OpenRemaster.ReadOnlyPortfolioHandoff.v11",
 "operation_id":d["operation_id"],"iteration_id":d["iteration_id"],"run_id":d["run_id"],
 "status":"NEW_STATIC_SOURCE_CONTRACTS_VERIFIED_RUNTIME_FIDELITY_HOLD",
 "artifact_role":"ISOLATED_REPORT_NOT_ACCEPTANCE_CHECKPOINT",
 "predecessor_handoff_sha256":fp(PRIOR),"registry_sha256":fp(REG),
 "semantic_delta_sha256":fp(RUN/"SEMANTIC_DELTA.json"),
 "static_validation_sha256":fp(RUN/"STATIC_VALIDATION.json"),
 "source_identity":{
  "original_exe_pins":3,
  "source_region_hashes":v["source_regions_checked"],
  "static_opcode_fixture_and_relocation_checks_total":v["original_instruction_and_fixture_checks"],
  "relocation_checks_in_total":v["ne_relocations_checked"],
  "scope":"Static disassembly and standalone pure policy fixture tests, no game original-instruction execution"
 },
 "portfolio":portfolio,
 "execution":d["execution"],
 "preservation":d["preservation"],
 "environment_observation":d["environment_observation"],
 "policy":{
  "max_heavy_lanes":3,"wip_per_project":1,
  "focus_not_native_admission":True,
  "native_orch_k003_k004_admission":"NOT_REQUESTED_OR_GRANTED",
  "original_runtime_capture_authority":"NOT_PROVIDED",
  "dedicated_worker_effective_token_verified":False,
  "phase1":"FROZEN_UNCHANGED",
  "writer_scope":"This new CONT11 reports directory only; no project execution writer"
 },
 "source_static_restore_recipe":{
  "verify_against_pinned_originals":d["project_source_sha256"],
  "verify_registry_and_predecessor":True,
  "python_command":"python -B verify_cont11_static.py",
  "expected_receipt_status":v["status"],
  "note":"Smoke test for static source mechanisms only; NOT a certified game RehydrationContract or runtime restoration."
 },
 "tool_fingerprint":{
  "python":sys.version.split()[0],
  "capstone":capstone.__version__,
  "verifier_sha256":fp(RUN/"verify_cont11_static.py"),
  "finalizer_sha256":fp(Path(__file__))
 },
 "fresh_runtime_fidelity_pass":0,
 "written_at_utc":now
}
handoff=RUN/"READ_ONLY_HANDOFF.json"
with handoff.open("x",encoding="utf-8") as f:
    json.dump(receipt,f,indent=2,sort_keys=True)
    f.write("\n")

summary=f"""# OpenRemaster CONT11 — read-only source mechanisms

- Run: `{d['run_id']}`
- Operation: `{d['operation_id']}`
- Scope: source-static evidence. **NOT game runtime, fidelity or admission PASS**.
- Portfolio: **23/23** preserved, including Retail PAUSED / Demo CLOSED.
- Checks: **21 source byte-range hashes; 115 static opcode, model and relocation checks in total, including 10 NE relocations**.
- Original game/emulation jobs: **0**. Heavy jobs/builds/captures: **0**.

## OpenMDK1 — clipped polygon → triangle fan

The original source uses ordered clipping-plane bits 0x04, 0x01 and 0x02
following the earlier near-plane pass. At 0x40D8B5 the terminal polygon
must contain at least 3 vertices; at 0x40D8C3 the accumulated mask must be
zero. The source has six explicit calls to 0x40C860 (0x40D920, 0x40D95B,
0x40D993, 0x40D9CE, 0x40DA0F, 0x40DA44). For 3..8 vertices, they form a
vertex0-anchored fan of N-2 triangles with corresponding UV pointers.

**Open:** execute a bounded original clipped-LEVEL3 triangle replay under
admission, then test visual ordering and selected live raster profile.

## OpenStonekeep — event8 request → queue service → loader

0x31615 directly calls 0x85220. That handler processes the first queue
entry, conditionally dispatching to event8 at 0x853A0 and removing the
head via 0x85079 only after success. Event8 uses source/target *levels*
but stage row/col/facing remain separate globals. The loader's equal-level
path skips the examined transfer; h415's intended distinct-level path
still requires the original helper/queue and staged-generation evidence.

**Open:** show the real service/reentry ordering and preserved generation
between successful queue admission and loader transfer.

## OpenUltima8 — membership state and grid snapshot differ

The original conditional area update calls GLOB activation before its
own conditional grid rebuild at NE29:0x1D92. Nested immediate placement
may splice an item into the live sector head at NE29:0x273E and query
the existing grid at NE29:0x27D9. The direct splice→query source interval
only calls the height getter, not the grid producer. Do **not** force an
eager rebuild at every splice: original temporal semantics may read a
previous grid snapshot.

**Open:** actual grid generation/content, original fast-area callback
effects and live Map5 instance membership trace under approved runtime
and capture authority.

## Production and ownership boundaries

Canonical source bytes unchanged. The examined EXEs have ReadOnly attribute
false, while the named OpenRemasterWorker inherited allow rule is
ReadAndExecute; effective token and complete corpus ACL have not been newly
certified. No writer, ticket, lease, shared journal, frozen framework baseline
or warm project status was modified.

Files: `SEMANTIC_DELTA.json`, `verify_cont11_static.py`,
`STATIC_VALIDATION.json`, `READ_ONLY_HANDOFF.json`, and `manifest.json`.
"""
md=RUN/"CONT11_SUMMARY.md"
with md.open("x",encoding="utf-8") as f:f.write(summary)

manifest=RUN/"manifest.json"
m=json.loads(manifest.read_text(encoding="utf-8-sig"))
m.update(
    operation_id=d["operation_id"],
    iteration_id="CONT11",
    artifact_role="READ_ONLY_STATIC_REPORT_NOT_ACCEPTANCE_OR_PRODUCTION_ADMISSION",
    source_exes_pinned=3,source_region_checks=21,static_checks=115,
    outputs=[{"file":n,"sha256":fp(RUN/n),"role":"STATIC_SOURCE_EVIDENCE_OR_REPORT_ONLY"}
        for n in ("SEMANTIC_DELTA.json","verify_cont11_static.py",
                  "STATIC_VALIDATION.json","complete_cont11_handoff.py",
                  "READ_ONLY_HANDOFF.json","CONT11_SUMMARY.md")]
)
manifest.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
assert all(fp(RUN/x["file"])==x["sha256"] for x in m["outputs"])
assert len(json.loads(handoff.read_text())["portfolio"])==23
print(json.dumps({"status":"PASS_PORTFOLIO_23_AND_REPORT_MANIFEST_ONLY",
 "run_id":d["run_id"],
 "static_evidence_class":v["status"],
 "portfolio":23,"original_exes":3,"source_regions":21,"static_checks_total":115,
 "relocations_included":10,"game_tests":0,
 "files":{n:fp(RUN/n) for n in ("SEMANTIC_DELTA.json","STATIC_VALIDATION.json",
   "READ_ONLY_HANDOFF.json","CONT11_SUMMARY.md","manifest.json")}},sort_keys=True))
