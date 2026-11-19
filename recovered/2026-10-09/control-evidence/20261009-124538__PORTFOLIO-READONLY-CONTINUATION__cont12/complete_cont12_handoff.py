"""Finalize CONT12 isolated read-only evidence handoff, preserving all 23 lanes."""
from pathlib import Path
import hashlib,json,datetime,copy,sys,capstone
ROOT=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=ROOT/"output/projects/OpenRemasterOrchestrator/reports/20261009-122230__PORTFOLIO-READONLY-CONTINUATION__cont11/READ_ONLY_HANDOFF.json"
REG=ROOT/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
delta=json.loads((HERE/"SEMANTIC_DELTA.json").read_text(encoding="utf-8"))
validation=json.loads((HERE/"STATIC_VERIFICATION.json").read_text(encoding="utf-8"))
prior=json.loads(PREV.read_text(encoding="utf-8-sig"))
assert digest(PREV)==delta["previous_handoff_sha256"]
assert digest(REG)==delta["portfolio_registry"]["sha256"]
assert prior["operation_id"]==delta["operation_id"]
assert validation["delta_sha256"]==digest(HERE/"SEMANTIC_DELTA.json")
assert validation["status"]=="PASS_SOURCE_STATIC_INSTRUCTION_AND_PURE_CONTRACT_FIXTURES_ONLY"
assert validation["source_regions"]==16
assert validation["source_opcode_checks"]==70
assert validation["stonekeep_queue_pure_fixtures"]==52
assert validation["stonekeep_event8_accepted_fixtures"]==46
assert validation["stonekeep_event8_rejected_fixtures"]==6
assert validation["ne_relocations_scanned"]==12274
assert len(validation["ne_grid_direct_far_callers"])==6
assert not validation["original_game_runtime_or_capture_executed"]
assert validation["original_game_instructions_executed"]==0
assert delta["preservation"]["portfolio_records"]==23

rows=copy.deepcopy(prior["portfolio"])
assert len(rows)==23 and len({r["project"] for r in rows})==23
before_lanes={e["project"]:e["lane"] for e in rows}
for item in rows:
    p=item["project"]
    if p in delta["focus"]:
        c=delta["focus"][p]
        item.update(
            status=c["state"],
            progress=c["delta"],
            next=c["next"],
            evidence_class="NEW_SOURCE_STATIC_AND_PURE_CONTRACT_FIXTURE_NOT_GAME_RUNTIME"
        )
    elif p=="OpenRemasterOrchestrator":
        item.update(
            status="CONTROL_PLANE_REPORT_ONLY_PRODUCTION_NOT_ADMITTED",
            progress="Persisted isolated CONT12 source-static evidence, verifier and 23-project handoff; no job, lease or journal admission",
            next="Continue game-driven narrow blockers only; no duplicate writer or heavy dispatch",
            evidence_class="REPORT_ONLY_NOT_ACCEPTANCE_CHECKPOINT"
        )
    else:
        item["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED_OR_DISPATCHED"
assert len(rows)==23 and before_lanes=={e["project"]:e["lane"] for e in rows}
assert next(e for e in rows if e["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(e for e in rows if e["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(e for e in rows if e["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
assert sum(e["lane"]=="FOCUS_READ_ONLY" for e in rows)==3

now=datetime.datetime.now(datetime.timezone.utc).isoformat()
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v12",
 "operation_id":delta["operation_id"],
 "iteration_id":"CONT12",
 "run_id":delta["run_id"],
 "status":"NEW_SOURCE_STATIC_EVIDENCE_COMPLETE_RUNTIME_FIDELITY_HOLD",
 "artifact_role":"READ_ONLY_REPORT_NOT_GAME_ACCEPTANCE_OR_PRODUCTION_ADMISSION",
 "predecessor_handoff_sha256":digest(PREV),
 "registry_sha256":digest(REG),
 "semantic_delta_sha256":digest(HERE/"SEMANTIC_DELTA.json"),
 "static_verification_sha256":digest(HERE/"STATIC_VERIFICATION.json"),
 "portfolio":rows,
 "source_evidence":{
    "original_exes":3,
    "original_static_byte_regions":validation["source_regions"],
    "original_static_opcode_checks":validation["source_opcode_checks"],
    "ne_relocations_scanned":validation["ne_relocations_scanned"],
    "direct_grid_far_builder_calls":4,
    "direct_grid_far_query_calls":2,
    "stonekeep_pure_state_fixtures":52,
    "mdk_convex_bound_fixtures":6,
    "u8_list_model_fixtures":4,
    "no_game_instruction_executed":True
 },
 "execution":delta["execution"],
 "preservation":delta["preservation"],
 "admission":{
   "native_ORCH_K003_K004":"NOT_RECHECKED_OR_GRANTED",
   "source_effective_worker_token":"NOT_FRESHLY_CERTIFIED",
   "source_corpus_policy":"READ_ONLY_NOT_MUTATED",
   "no_new_writer":True,
   "no_new_native_job":True,
   "fidelity_authority_capture":"NONE"
 },
 "reproduce":{
   "root":"F:\\Remaster Framework",
   "recipe":"python -B verify_cont12_static.py",
   "expected_status":validation["status"],
   "method":"Statically read original PE/LE/NE source against SHA-256 pins, enumerate far NE fixups, run pure model fixtures",
   "output_sha256_file":"STATIC_VERIFICATION.json",
   "not_equivalent_to_game_rehydration_contract":True
 },
 "runtime_fidelity_accepted":False,
 "written_at_utc":now,
 "tools":{
   "python_version":sys.version.split()[0],
   "capstone_version":capstone.__version__,
   "verify_script_sha256":digest(HERE/"verify_cont12_static.py")
 }
}
hp=HERE/"READ_ONLY_HANDOFF.json"
with hp.open("x",encoding="utf-8") as f:json.dump(handoff,f,indent=2,sort_keys=True);f.write("\n")

summary=f"""# OpenRemaster — CONT12 | read-only semantic continuation

**9. októbra 2026 · Originálne súbory ponechané nezmenené**

Operation ID: `{delta['operation_id']}`  
Run ID: `{delta['run_id']}`  
Portfólio: **23/23**. Fokus: **OpenMDK1, OpenStonekeep, OpenUltima8**.

## OpenStonekeep — presná queue-admission hranica h415

Doložený vstup pred event8: `0xA2C4A` vždy požaduje jednu udalosť cez
`0x85139`; argumentová vetva `==1` pridáva ešte dve požiadavky cez
`0x851C3`; event8 príde až na `0xA2C91`. Kapacita frontu je 25.

| Počiatočné obsadenie | Bez extra udalostí | S dvoma extra udalosťami |
|---|---|---|
| 0–21 | event8 prijatý | event8 prijatý |
| 22–23 | event8 prijatý | event8 odmietnutý |
| 24–25 | event8 odmietnutý | event8 odmietnutý |

52 čisto modelových fixtures: 46 prijatí a 6 odmietnutí. **Nie je to
spustená hra ani dokázaný softlock.** Neznáme ostávajú event-service
reentrancy a identita globálneho staged payloadu.

## OpenUltima8 — dva odlišné priechody zoznamom

Prvý priechod `NE29:0x272` je podmienený `DS:0x1A26`. Pre property3
a nenulový návrat z `NE28:0xC81` môže vyvolať GLOB aktiváciu.
Po callbacku načíta `next[current]` z aktuálneho zoznamu.

Druhý priechod *znovu číta sektorovú hlavu* v `NE29:0x365`, takže môže
vidieť objekty vytvorené prvým priechodom. Na `NE29:0x37B` volá
`NE28:0x2577` a následne opäť číta aktuálny next.

Z celého pôvodného korpusu 12 274 NE fixup záznamov sú doložené
**4 priame far volania grid buildera** a **2 grid predikátu**.
Nejde o úplnú analýzu nepriameho/transitívneho callgraphu.
Živá grid epoch, membership a runtime fidelity zostávajú neoverené.

## OpenMDK1 — oprava počtu clipping rovín

Originálne clipping masky: `0x10 → 0x08 → 0x04 → 0x01 → 0x02`.
Predchádzajúci zoznam vynechal `0x08`.

Ping-pong source vertex buffery: krok `0xF0` (10 miest po 24 B).
UV buffery: krok `0x50` (10 miest po 8 B).
Matematický limit pôvodného konvexného trojuholníka pri piatich
polrovinách: najviac 8 vrcholov, fan najviac 6 trojuholníkov.
Toto korešponduje so šiestimi explicitnými originálnymi volaniami
`0x40C860`. Nejde o pôvodnú runtime pixelovú verifikáciu.

## Validácia a execution

- Pôvodné EXE: **3**, zhodné SHA-256.
- Zdrojové úseky: **16**, hashová identita PASS.
- Pôvodné inštrukcie: **{validation['source_opcode_checks']} statických kontrol**.
- Stonekeep: **52 čisto modelových fixtures**.
- MDK1: 6 čistých geometrických fixtures; Ultima8: 4 čisto modelové fixtures.
- NE relokačné záznamy prehľadané: **12 274**.
- Herne vykonané inštrukcie/runtime/build/capture/heavy job: **0**.

Azrael Retail: PAUSED (žiadny writer-lock repoll). Demo: CLOSED.
ROTH: WARM_COMPLETION. Phase 1 Frameworku: FROZEN.
Produkčné admission nebolo udelené ani testované, writery/tickets/leases
ani shared journal neboli modifikované.

**Ďalší blocker:** U8 `NE28:0x2577` state delta pri druhom priechode;
Stonekeep event8 service a staged generation; MDK1 reálna LEVEL3
clipped-triangle replay s autoritatívnym runtime comparatorom.
"""
sp=HERE/"CONT12_SUMMARY.md"
with sp.open("x",encoding="utf-8") as f:f.write(summary)

mp=HERE/"manifest.json"
m=json.loads(mp.read_text(encoding="utf-8-sig"))
m.update(
 operation_id=delta["operation_id"],iteration_id="CONT12",
 artifact_role="PERSISTENT_READ_ONLY_SOURCE_STATIC_HANDOFF_NO_ADMISSION",
 predecessor_handoff_sha256=delta["previous_handoff_sha256"],
 outputs=[{"file":name,"sha256":digest(HERE/name),"role":"REPORT_OR_STATIC_SOURCE_VERIFICATION_ONLY"}
          for name in ("SEMANTIC_DELTA.json","verify_cont12_static.py","STATIC_VERIFICATION.json",
                       "complete_cont12_handoff.py","READ_ONLY_HANDOFF.json","CONT12_SUMMARY.md")]
)
mp.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8")
assert all(digest(HERE/r["file"])==r["sha256"] for r in m["outputs"])
assert len(json.loads(hp.read_text(encoding="utf-8"))["portfolio"])==23
assert digest(PREV)==delta["previous_handoff_sha256"] and digest(REG)==delta["portfolio_registry"]["sha256"]
print(json.dumps({"status":"PASS_REPORT_STRUCTURE_AND_SOURCE_STATIC_ONLY","portfolio_entries":23,
"source_regions":16,"source_opcode_checks":validation["source_opcode_checks"],
"stonekeep_pure_fixtures":52,"u8_direct_grid_calls":6,"native_game_tests":0,
"artifact_hashes":{k:digest(HERE/k) for k in ("SEMANTIC_DELTA.json","STATIC_VERIFICATION.json","READ_ONLY_HANDOFF.json","CONT12_SUMMARY.md","manifest.json")},
"run_id":delta["run_id"]},sort_keys=True))
