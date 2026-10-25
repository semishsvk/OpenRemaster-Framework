# OpenRemaster — Game Logic & Completion Assurance Workflow v1.0
Date: 2026-10-25
Status: APPROVED REQUIREMENT; ISOLATED SHADOW POLICY; production enforcement NOT commissioned.

## Scope
All existing and future OpenRemaster game projects. Preserve original story, mechanics, puzzles, timing, scripts, state, intended dead ends, and save semantics. Canonical game corpora STRICT READ-ONLY.

## Required pipeline
1. Source-bound World Discovery: inventory rooms, objects, actors, hotspots, cameras, items, save structures, and room edges with SHA-256 provenance and confidence.
2. Logic Reconstruction: build conditional script CFG, event and object-state dependencies, inventory ownership, actor movement, scheduler callbacks, globals and cross-room side effects. Never confuse source alternatives with executed traces.
3. Completion Contract: identify authentic victory and loss predicates, endings, terminal scripts and prerequisites; if unknown mark UNKNOWN, never fabricate.
4. Reachability & Reversibility: explore bounded state transitions and backwards dependencies from each proven ending. Classify reachable, recoverable, unreachable, unproven, intended dead end; preserve alternative actors and paths.
5. Softlock Risk Registry: LOST_CRITICAL_ITEM, UNRECOVERABLE_OWNERSHIP, IRREVERSIBLE_PUZZLE, STRANDED_CHARACTER, BROKEN_DOOR_STATE, UNREACHABLE_INTERACTION, SCRIPT_DEADLOCK, INVENTORY_TRAP, MISSED_TIMED_OPPORTUNITY, BROKEN_ACTOR_HANDOFF, SAVE_STATE_CORRUPTION, UNREACHABLE_ENDING. Static candidates are NOT proven softlocks.
6. Authentic Replay: original engine/reference run vs remaster event traces, actor/object/global state, room transitions, save/load, visuals, audio and timing. Capture earliest causal divergence; never infer runtime acceptance from screenshots alone.
7. Acceptance Gates: SOURCE_ONLY, STATIC_CANDIDATE, RUNTIME_REFERENCE_VERIFIED, REMASTER_REPLAY_VERIFIED, INDEPENDENT_ACCEPTED; UNKNOWN and HOLD remain explicit. Critical broken room transitions and new reachable unwinnable states block production release.

## Evidence contract
Per finding: project/game/version/source hashes; original vs remaster; starting save/state and reproduction actions; room, actor, item and script IDs; state variables and timestamps; candidate vs proven; reference traces; proof of reachable path; proof of no permitted path to victory when claiming a hard softlock; confidence; reversibility; expected behavior; root cause; regression test; owner/writer admission and immutable evidence digest.

## Safety and rollout
SHADOW_ONLY by default. Isolated development worker may run bounded analysis under per-project owner lease, single writer, governor, resource limits and audit. Production build requires signed trusted worker, independent gates, clean pinned rebuild and separate release authorization under Dual-Trust Worker Architecture v1.0. No production enforcement, shared canonical modification, active orchestration, or signature claims without explicit owner admission and independent validation. Use CACHE -> DIFF -> IMPACT -> FAST -> VERIFY -> BUILD -> CANDIDATE with minimal heavy slots. Missing evidence => HOLD, never auto-accept.

## OpenZak pilot baseline
K112-R48 source graph: 58 rooms with objects, 770 object records, 576 programs, 2576 effect records. K112-R49: 1743 broad static risk records, 0 proven softlocks. K112-R50: victory predicate not yet verified. The pilot must not imply that the whole game is replay-tested or winnable.

## Acceptance negative tests
Reject: static risk labeled confirmed softlock; missing victory predicate labeled full coverage; source-only path labeled native replay; unknown actor owner treated as Zak; one screenshot accepted as script trace; intended original dead end silently patched; new softlock classified as intended; missing save/load roundtrip; missing production worker attestation; missing independent verification; evidence hash drift; conflicting owner; unsigned DEV artifact promoted to release.
