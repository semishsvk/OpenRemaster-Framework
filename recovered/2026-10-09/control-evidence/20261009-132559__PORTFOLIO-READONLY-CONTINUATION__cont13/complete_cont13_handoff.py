"""Finalize the single-writer, append-only CONT13 report handoff.

Preserves all 23 portfolio rows and writes nothing outside this unique
reports directory. A static-source PASS is never a runtime/fidelity PASS.
"""
from pathlib import Path
import json,hashlib,datetime,copy,sys,capstone
BASE=Path(r"F:\Remaster Framework")
HERE=Path(__file__).resolve().parent
PREV=BASE/"output/projects/OpenRemasterOrchestrator/reports/20261009-124538__PORTFOLIO-READONLY-CONTINUATION__cont12/READ_ONLY_HANDOFF.json"
REG=BASE/"orchestrator/control-plane/portfolio-lanes-20261008-v3.json"
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def jload(p):return json.loads(p.read_text(encoding="utf-8-sig"))
main=jload(HERE/"SEMANTIC_DELTA.json")
result=jload(HERE/"STATIC_VERIFICATION.json")
markers=jload(HERE/"U8_MAP5_SPECIAL_MARKERS.json")
pair=jload(HERE/"U8_GLOB218_PAIRED_SOURCE_FIXTURE.json")
prior=jload(PREV)
assert SHA(PREV)==main["predecessor_handoff_sha256"]
assert SHA(REG)==main["registry_sha256"]
assert prior["operation_id"]==main["operation_id"]
assert len(prior["portfolio"])==23 and len({r["project"] for r in prior["portfolio"]})==23
assert len([r for r in prior["portfolio"] if r["lane"]=="FOCUS_READ_ONLY"])==3
assert result["status"]=="PASS_SOURCE_STATIC_IDENTITY_WITH_CONDITIONAL_FLAG_BIT7_CONTRACTS"
assert result["source_region_count"]==16 and result["static_opcode_and_relocation_check_count"]==71
assert len(result["pure_u8_flag_fixtures"])==40 and len(result["pure_stonekeep_poll_fixtures"])==4
assert result["derived_marker_manifest_sha256"]==SHA(HERE/"U8_MAP5_SPECIAL_MARKERS.json")
assert result["original_game_instructions_executed"]==0 and not result["runtime_capture_fidelity_verified"]
assert len(markers["markers"])==148 and markers["bit7_set_potential_children"]==2360
assert len(pair["markers"])==2 and pair["expected_special_count"]==24 and pair["expected_ordinary_count"]==8
assert pair["markers"][0]["marker_id"]=="fixed:m5:r2378"
assert pair["markers"][0]["special_example"]["source_instance_id"]=="fixed:m5:r2378:g218:s0"
assert pair["markers"][0]["ordinary_example"]["source_instance_id"]=="fixed:m5:r2378:g218:s12"
assert set(main["focus"])=={"OpenMDK1","OpenStonekeep","OpenUltima8"}
assert main["execution"]["new_heavy_jobs"]==0 and main["execution"]["new_runtime"]==0
assert main["execution"]["new_original_game_instruction_tests"]==0 and main["execution"]["new_builds"]==0

rows=copy.deepcopy(prior["portfolio"])
baseline_lanes={r["project"]:r["lane"] for r in rows}
for row in rows:
    project=row["project"]
    if project in main["focus"]:
        f=main["focus"][project]
        row.update(
            status=f["state"],progress=f["delta"],next=f["next"],
            evidence_class="NEW_SOURCE_STATIC_CONTRACT_AND_POTENTIAL_MAP5_CENSUS_NOT_RUNTIME"
        )
    elif project=="OpenRemasterOrchestrator":
        row.update(
            status="CONTROL_PLANE_REPORT_ONLY_NATIVE_PRODUCTION_NOT_ADMITTED",
            progress="CONT13 report-only validation; Map5 bit7 subpopulation and concrete paired special/ordinary source case; no native job",
            next="Consume CONT13 with same operation identity; maintain isolated writer ownership and existing scheduling",
            evidence_class="REPORT_ONLY_NOT_ACCEPTANCE"
        )
    else:
        row["evidence_class"]="CARRIED_FORWARD_NOT_REPOLLED_OR_EXECUTED"
assert len(rows)==23 and {r["project"]:r["lane"] for r in rows}==baseline_lanes
assert next(r for r in rows if r["project"]=="OpenAzrael-Retail")["lane"]=="WARM_WAIT_EXTERNAL"
assert next(r for r in rows if r["project"]=="OpenAzrael-Demo")["lane"]=="CLOSED_ARCHIVED"
assert next(r for r in rows if r["project"]=="OpenROTH")["lane"]=="WARM_COMPLETION"
timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
handoff={
 "schema":"OpenRemaster.PortfolioReadOnlyHandoff.v13",
 "operation_id":main["operation_id"],"iteration_id":"CONT13","run_id":main["run_id"],
 "status":"NEW_SOURCE_STATIC_CONTRACTS_AND_MAP5_SPECIAL_SUBPOPULATION_VERIFIED_RUNTIME_FIDELITY_HOLD",
 "artifact_role":"READ_ONLY_REPORT_NOT_GAME_ACCEPTANCE_OR_ORCH_K003_NATIVE_ADMISSION",
 "previous_handoff_sha256":SHA(PREV),"portfolio_registry_sha256":SHA(REG),
 "evidence_sha256":{
  "SEMANTIC_DELTA.json":SHA(HERE/"SEMANTIC_DELTA.json"),
  "STATIC_VERIFICATION.json":SHA(HERE/"STATIC_VERIFICATION.json"),
  "U8_MAP5_SPECIAL_MARKERS.json":SHA(HERE/"U8_MAP5_SPECIAL_MARKERS.json"),
  "U8_GLOB218_PAIRED_SOURCE_FIXTURE.json":SHA(HERE/"U8_GLOB218_PAIRED_SOURCE_FIXTURE.json")
 },
 "source_checks":{
  "whole_original_exes":3,
  "additional_verified_original_inputs":["TYPEFLAG.DAT","map5-materialization-sourceir-v3.json"],
  "source_regions":16,
  "opcode_and_far_relocation_checks":71,
  "pure_u8_flag_cases":40,
  "pure_stonekeep_poll_cases":4,
  "Map5_glob_potential":17774,
  "Map5_byte0_bit7_special":2360,
  "Map5_special_marker_definitions":148,
  "source_scope_only":True
 },
 "portfolio":rows,
 "execution":main["execution"],
 "preservation":main["preservation"],
 "admission":{
  "ORCH_K003_K004":"NOT_RECHECKED_OR_GRANTED",
  "native_worker_commissioning":"NOT_RECHECKED",
  "game_runtime_authority":"NOT_INVOLVED",
  "original_source_write":False,
  "writer_lease_or_ticket_created":False,
  "global_job_count":"NOT_RECOUNTED",
  "replay_or_fidelity_pass":False
 },
 "reproduction":{
  "recipe":["python -B verify_cont13_static.py","python -B derive_paired_fixture.py"],
  "source_hashes":{key:detail["sha256"] for key,detail in result["source_inputs"].items()},
  "expected_verification":result["status"],
  "deterministic_existing_output_policy":"Byte-compare existing outputs; do not overwrite",
  "not_full_game_rehydration_contract":True,
  "python_version":sys.version.split()[0],
  "capstone_version":capstone.__version__,
  "static_verifier_sha256":SHA(HERE/"verify_cont13_static.py"),
  "paired_fixture_generator_sha256":SHA(HERE/"derive_paired_fixture.py")
 },
 "recorded_at_utc":timestamp
}
hp=HERE/"READ_ONLY_HANDOFF.json"
with hp.open("x",encoding="utf-8") as f:
    json.dump(handoff,f,indent=2,sort_keys=True,ensure_ascii=False);f.write("\n")

summary=f"""# OpenRemaster — CONT13 | 9. október 2026

**Status:** Source-static contracts verified; **game runtime, visual fidelity and production admission BLOCKED**.  
**Operation ID:** `{main['operation_id']}`  
**Run ID:** `{main['run_id']}`  
**Portfólio:** 23/23 zachované. Fokus: OpenUltima8, OpenStonekeep, OpenMDK1.

## 1. OpenUltima8 — reálny lifecycle blocker už má konkrétnu source podskupinu

Original `NE28:0x2577` najprv načíta príznaky, pridá bit `0x2000` a
volá `NE28:0x1F70`, ktorá zapíše výsledné flags do `ACD3[item]`.
**Platí pri normálnom návrate pomocných rutín.**

`NE28:0x1EBC` je iba test **1 ≤ handle ≤ 255**. Nie je dôkazom
členstva v sektore. Veta „druhý priechod iba číta“ je preto nesprávna.

Pri family0, handle ≥ 256 a nenulovom aktívnom area kontexte rozhoduje
`TYPEFLAG[shape].byte0 & 0x80` o možnosti volania
`NE126:0xBF7`. Aj táto rutina má ďalšie podmienky:
`DS:0x8906` a `DS:0x88F6`. Skutočný počet volaní je **NEZNÁMY**.

Pre Map5 `map5-materialization-sourceir-v3.json` s autoritatívnym
`TYPEFLAG.DAT` sú doložené tieto **potenciálne**, nie živé populácie:

| Trieda | Počet potenciálnych detí |
|---|---:|
| Všetky GLOB family0 | 17 774 |
| Byte0 bit7 = 1, jediný shape347 | 2 360 |
| Byte0 bit7 = 0 | 15 414 |

Špeciálne deti pochádzajú zo **148 FIXED GLOB značiek**:
GLOB262 má **2 336**, GLOB218 má **24** takýchto detí.
Zároveň GLOB218 obsahuje **8 bežných detí shape128** bez bitu.
Byte1 low bit (2620 výskytov) je odlišný od Byte0 bit7 a tieto dve
dimenzie nemožno zameniť.

### Najmenší autentický párový zdroj

`fixed:m5:r2378:g218:s0` — shape347 / špeciálna podmienka.  
`fixed:m5:r2378:g218:s12` — shape128 / bez špeciálnej podmienky.

Sú to dve deti z rovnakej GLOB značky `fixed:m5:r2378`
(12 špeciálnych, 4 bežné), vhodné na **budúcu izolovanú validáciu**.
Rovnaký mix má `fixed:m5:r2379`. Nemajú zatiaľ preukázané runtime ID,
aktiváciu ani vizuálnu fidelity.

**Next:** pri schválenom native admission získať pôvodný handle/area
trace tohto páru, overiť `NE126:0xBF7` a konečné sektorové členstvo
pred/po grid rebuild. SourceIR nie je live occupancy.

## 2. OpenStonekeep — input pump odkladá event queue service

Pôvodný orchestrujúci kód pri `0x3160B` volá `0x32BFF`,
pri nenulovom AX volanie opakuje, a až po nulovom AX na `0x31615`
volá `0x85220` — obsluhu predného eventu.

To preukazuje možné **odloženie service**, nie automatický ďalší
h415 staging. Reentry/overwrite zostáva explicitne **UNVERIFIED**.

**Next:** dokázať alebo falsifikovať transitive callback cestu zo
`0x32BFF` k opätovnému h415 staged payloadu. Bez toho nepromovať
E.16 hranu na úplný prejdený prechod.

## 3. OpenMDK1 — jeden signed-f3 pre celý clipped fan

Šesť source load/push/call trojíc od `0x40D8F5` po `0x40DA44`
každá odovzdáva pôvodný `[EBP+0x10]` signed-f3 argument do
`0x40C860`. V sorter rutine sa tento argument číta cez
`[EBP+0x18]`. Rekonštrukcia nesmie pre nové fan trojuholníky
vymýšľať material index ani znovu zavádzať falsifikované modulo.

**Next:** konkrétny original-runtime clipping/camera/profile replay
a pixelový comparator, až po povolenom admission.

## 4. Statický audit a ochrana

- **3 originálne EXE + TYPEFLAG + Map5 SourceIR** overené SHA-256.
- **16/16 source byte úsekov** a **71 original-opcode/far-fixup kontrol**.
- **40 čistých flag modelových** a **4 čisté input-pump modelové fixtures**.
- **148 konkrétnych zdrojových značiek** s bit7 = 1 v sprievodnom JSON.
- Nové original-instruction emulačné testy, runtime, buildy, heavy joby, captures: **0**.
- Azrael Retail **PAUSED**; Demo **CLOSED**; ROTH **WARM_COMPLETION**;
  Phase 1 **FROZEN**.
- Žiadne zmeny canonical corpusu, projektu, shared job journalu,
  writer/ticket/lease alebo automatizácií.

**Verdikt:** PASS source-static identity a podmienených kontraktov.
Nie nový playable, runtime, fidelity alebo release PASS.
"""
sp=HERE/"CONT13_SUMMARY.md"
with sp.open("x",encoding="utf-8") as f:f.write(summary)
manifest_path=HERE/"manifest.json"
m=json.loads(manifest_path.read_text(encoding="utf-8-sig"))
m.update(
    operation_id=main["operation_id"],iteration_id="CONT13",
    artifact_role="PERSISTENT_READ_ONLY_ORIGINAL_SOURCE_REPORT_NOT_ACCEPTANCE_OR_ADMISSION",
    predecessor_handoff_sha256=main["predecessor_handoff_sha256"],
    outputs=[{"file":name,"sha256":SHA(HERE/name),"role":"SOURCE_STATIC_REPORT_OR_REPRODUCIBLE_CORPUS_PROJECTION"}
      for name in ("verify_cont13_static.py","derive_paired_fixture.py","complete_cont13_handoff.py",
       "STATIC_VERIFICATION.json","U8_MAP5_SPECIAL_MARKERS.json","U8_GLOB218_PAIRED_SOURCE_FIXTURE.json",
       "SEMANTIC_DELTA.json","READ_ONLY_HANDOFF.json","CONT13_SUMMARY.md")]
)
manifest_path.write_text(json.dumps(m,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
assert all(SHA(HERE/x["file"])==x["sha256"] for x in m["outputs"])
assert len(json.loads(hp.read_text(encoding="utf-8"))["portfolio"])==23
assert SHA(REG)==main["registry_sha256"] and SHA(PREV)==main["predecessor_handoff_sha256"]
print(json.dumps({"status":"PASS_23_PORTFOLIO_REPORT_MANIFEST_ONLY",
                   "run_id":main["run_id"],"source_region_checks":16,
                   "source_opcode_relocation_checks":71,
                   "glob_special_potential":2360,"marker_definitions":148,
                   "paired_markers":2,"original_game_runtime_tests":0,
                   "files":{n:SHA(HERE/n) for n in ("SEMANTIC_DELTA.json","STATIC_VERIFICATION.json",
                     "U8_MAP5_SPECIAL_MARKERS.json","U8_GLOB218_PAIRED_SOURCE_FIXTURE.json",
                     "READ_ONLY_HANDOFF.json","CONT13_SUMMARY.md","manifest.json")}},sort_keys=True))
