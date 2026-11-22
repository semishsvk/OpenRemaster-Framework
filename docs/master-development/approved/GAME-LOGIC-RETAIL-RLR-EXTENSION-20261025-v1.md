# OpenRemaster — Retail Logic Reconstruction Lab extension v1.0
Date: 2026-10-25
Status: USER APPROVED; SHADOW-ONLY WORKFLOW INTAKE; NOT PRODUCTION DEPLOYED
Parent: GAME-LOGIC-COMPLETION-ASSURANCE-20261025-v1.md
Plan: GAME-LOGIC-COMPLETION-ASSURANCE-WORK-PLAN-20261025.md

## Intent
Extend GLCA-001..008 rather than create a competing pipeline. OpenAzrael retail is the first complex pilot; reuse OpenZak source-bound decoder and graph principles. All original corpora are read-only.

## RLR workstream (after GLCA discovery)
RLR-01 Pin retail corpus files, versions, hashes, decoder coverage, provenance and original runtime configuration.
RLR-02 Enumerate rooms, objects, hotspots, NPCs, item ownership, transitions, animation/audio hooks and persistence.
RLR-03 Recover all dialogue options, guards, side effects, callbacks, hidden branches and unreachable/dead content. Separate proven facts from hypotheses.
RLR-04 Build canonical typed state IR with location, inventory, flags, NPC states, timers, world modifications, save/load and endings.
RLR-05 Extract puzzle dependency DAG, alternative solutions, irreversible decisions, cross-room effects and critical-item constraints.
RLR-06 Run bounded forward symbolic exploration plus backward solving from every independently established terminal predicate. State deduplication must preserve future-observable behavior, timers and relevant ownership.
RLR-07 Classify successful endings, death, recoverable failure, intentional dead ends, regressions, potential and proven softlocks. Proving a softlock requires reachable witness and justified absence of legal victory continuation within a validated complete model; otherwise UNKNOWN.
RLR-08 Differential replay against original executable and remaster with reproducible input sequence, save snapshots, first divergence and evidence digest.
RLR-09 Generate searchable atlas and machine-readable coverage report with source offsets and confidence.

## Integration contract
Map RLR-01/02 to GLCA-001; RLR-03/04 to GLCA-001/002; RLR-05/06 to GLCA-003; RLR-07 to GLCA-004; RLR-08 to GLCA-005/006; RLR-09 to GLCA-007. GLCA-008 remains independent production acceptance.
Suggested artifacts: corpus_manifest.json, world_graph.json, dialogue_ir.json, state_ir.json, puzzle_dependencies.json, ending_registry.json, path_witnesses.json, softlock_registry.json, replay_diffs.json, coverage_report.json. Schemas must be versioned and validated before consumer adoption.

## Trust, admission and rollout
SHADOW_ONLY. Use isolated project-specific workspace, owner lease, single-writer, CACHE->DIFF->IMPACT->FAST->VERIFY->BUILD->CANDIDATE, governor and bounded slots. DEVELOPMENT worker may perform isolated analysis without production secrets or signing rights. Production promotion requires signed trusted worker, independent evidence checks, clean pinned rebuild and explicit owner authorization. Never modify shared canonical workflow, runtime, Studio or original corpus without admission. No automatic rollout to other games.

## Pilot
OpenAzrael original retail corpus at F:\Remaster Framework\source\Azrael's Tear; independent OpenZak pilot remains intact. External walkthrough claims about endings are hypotheses until confirmed by source/runtime. Record source and execution coverage separately; 100% coverage may only be claimed against a clearly defined, fully inventoried scope.

## Next execution gate
Work/orchestrator owner must acknowledge intake, establish lease and pin baseline before code changes. This file is an additive handoff only, not evidence of active execution, tested solver, or completed retail analysis.
