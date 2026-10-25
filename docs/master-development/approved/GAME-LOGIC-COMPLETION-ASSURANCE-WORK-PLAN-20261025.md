# OpenRemaster Work development-plan addition — Game Logic & Completion Assurance
Date: 2026-10-25
Status: USER APPROVED / READY FOR WORK INTAKE / NOT CLAIMED ACTIVE

## Objective
Integrate the approved `GAME-LOGIC-COMPLETION-ASSURANCE-20261025-v1.md` into the existing Work development plan and OpenRemaster Framework workflow. This is an additive Work handoff, not an authorization to bypass owner admission, change canonical shared baselines, or claim live deployment.

## Ordered implementation tasks
GLCA-001 — Discovery contracts: canonical room/object/actor/inventory/script graph, source hashes, confidence and provenance; support incomplete corpus.
GLCA-002 — Completion predicates: original victory, loss, ending, terminal scripts; explicit UNKNOWN and alternative endings.
GLCA-003 — Dependency and reachability: reversible and irreversible transitions, bounded backward/forward analysis, multi-actor ownership, timers, saves.
GLCA-004 — Softlock registry: 12 approved categories, distinction between static candidate, confirmed original dead end, remaster regression, unresolved.
GLCA-005 — Authentic replay: source-bound event traces, first divergence, room/actor/inventory/script state, original-vs-remaster comparison.
GLCA-006 — Automated negative tests: missing victory, forged runtime evidence, source hash drift, actor handoff, broken transition, save/load, ownership and timing failures.
GLCA-007 — Orchestrator and Studio integration: isolated shadow-only results, evidence dashboard, owner approval, resource governor and project-scoped workflow. Do not expose technical IDs as primary UI labels.
GLCA-008 — Production acceptance: independently verified coverage and critical regression gates; Dual-Trust production worker, clean rebuild and signing authorization required before release enforcement.

## Pilot and rollout
Pilot OpenZak K112-R48/R49/R50; 58 rooms with catalogued objects, 770 objects, 576 programs, 2576 effect records, 1743 broad risk candidates, 0 confirmed softlocks, victory predicate UNKNOWN. Expand per-game only with independently verified corpus and project owner admission. Preserve original intentional unwinnable states; do not silently patch. No claims of full game completion from static indexes.

## Work handoff and acceptance
Import this file into the active Work development plan as a new workstream `Game Logic & Completion Assurance`. Cross-reference the approved v1 policy and existing `FrameworkGameCompletionEvidence-20261018-r1`. Execute GLCA-001..008 under CACHE→DIFF→IMPACT→FAST→VERIFY→BUILD→CANDIDATE, single writer, bounded heavy slots, GAME/LIGHT governor. Missing admission or evidence => HOLD. Report actual code/test artifacts separately from this planning document.
