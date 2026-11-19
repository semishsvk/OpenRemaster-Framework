# Consolidated development candidates

These modules are coordinated by **OpenRemaster — Master Development**. They are source candidates, not accepted production replacements.

| Module | Reused implementation | Current boundary |
| --- | --- | --- |
| GLCA | Existing core, source discovery, replay diagnostics and tests | Static/model-only; authentic game replay remains HOLD |
| Retail reconstruction | GLCA reachability, finding rules and dependency planner | Bounded corpus manifest, typed state, source-range IR, model witnesses and atlas; synthetic validation only |
| Dual Trust | Existing shadow handoff linter and DEV receipt crosswalk | No independent trust adapter; every release decision HOLD/REJECT |
| Workflow | Existing GLCA dependency/regression proposals | Advice for K003; no competing scheduler or dispatch |
| Native worker | Proven unsigned DEV broker, host and Rust supervisor source | Host-specific runtime/config/dependency pins excluded; not runnable until separately provisioned and admitted |
| Studio D7 | Source snapshot used by the successful DEV build | Historical D7 source; newer branding/UX source candidates remain separate |
| Authority intake | Existing R06 schema/binding/freshness validator | Structural checks only; it does not verify signatures or authorize dispatch |

No original game corpora, extracted game scripts, captured dialogues, local credentials, runtime databases or production signing material are included in this new source collection. `SOURCE_PROVENANCE.json` identifies the originally copied source bytes; later additive integration changes are versioned by Git.

Run `python -B scripts/development_acceptance.py --out <fresh-output-directory>` from the repository root. Test logs distinguish synthetic model evidence from authentic game validation. Existing Core acceptance remains a separate suite.

Native worker sources intentionally lack operational `WORKER-CONFIG.json`, dependency caches and machine tool paths. Do not remove their pin checks or invent production receipts to make them run. Reprovisioning belongs to the existing admitted worker workflow.

The historical `recovered/` code vault is preserved by a real Git merge. Its old launchers and security assumptions are not activated by inclusion here.
