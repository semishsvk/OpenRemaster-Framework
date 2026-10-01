# Framework vNext — Evidence-Driven Reconstruction

Status: APPROVED / IMPLEMENTATION HANDOFF
Prepared: 2026-10-01
Base: `integration/portfolio-consolidation-20261001 @ 007b3b6fe78eea978d07750138998dae52129177`
Implementation branch: `framework/vnext-evidence-driven-reconstruction`

## Boundary

Phase 1 remains frozen. vNext extends the existing Phase 2 implementation; it must not create a parallel evidence architecture.

Existing extension points:
- `src/openremaster/evidence.py`
- `src/openremaster/coverage.py`
- `src/openremaster/impact.py`
- `src/openremaster/bundle.py`
- existing store/provenance/replay/trace/reference-graph modules
- existing Phase 1/2 acceptance infrastructure

## Hard invariants

1. No VERIFIED claim without evidence.
2. No universal abstraction without cross-game validation.
3. Decoder non-observation never implies ABSENT.
4. No fidelity candidate without reproducible validation attestation.
5. Original corpora remain read-only.
6. Content identity is separate from occurrence/provenance/semantic identity.
7. Phase 1 acceptance must remain green and unchanged.

## Implementation checkpoint VNX-K001

Implement the first five approved primitives as extensions of the current model.

### A. Evidence Independence Graph
Add explicit immutable `EvidenceOrigin` and `EvidenceGroup` identities and claim-support edges. Correlated observations sharing an origin/group must not count as independent confirmations. Validation contracts may require a minimum number of independent groups.

### B. Negative Evidence Model
Canonical observation state:
`PRESENT | ABSENT_VERIFIED | NOT_OBSERVED | SOURCE_INCOMPLETE | DECODER_UNSUPPORTED | AMBIGUOUS`.

Fail closed. Existing pass/fail/unknown evidence remains readable; migrations/adapters must be deterministic.

### C. Decoder Coverage Contract
Add machine-readable decoder coverage with at least:
`discovered, recognized, decoded, structurally_validated, semantically_verified, unknown, rejected`.
Coverage must identify corpus/tool/decoder revision and evidence references. Parser success alone must never imply semantic verification.

### D. RuntimeEvidenceBundle v2
Extend ReplayEvidenceBundle rather than fork it. Bind replay contract, runtime trace, artifacts, build/corpus/scenario identities, validation contract and reproducibility metadata. Support deterministic canonical serialization/digest.

### E. Impact Graph v2
Extend advisory shadow impact into evidence-aware dependency closure. A change must resolve affected claims, artifacts, contracts and replay scenarios. vNext must initially remain fail-closed/advisory: it may select extra validation but may not silently suppress authoritative tests.

## Required schemas/types

Introduce, with deterministic canonical IDs where applicable:
- Claim / ClaimState: UNKNOWN, HYPOTHESIS, STRUCTURAL, VERIFIED, FALSIFIED, BLOCKED
- EvidenceOrigin
- EvidenceGroup
- ClaimSupport / ClaimContradiction
- ObservationState
- DecoderCoverageContract + DecoderCoverageReport
- ValidationContract reference
- RuntimeEvidenceBundle schema v2
- ImpactClosure

All IDs/digests must be stable across equivalent serialization.

## Acceptance VNX-K001

Required tests:
1. two observations from one EvidenceGroup count as one independent confirmation;
2. two independent groups can satisfy a contract requiring two;
3. NOT_OBSERVED cannot promote a claim to ABSENT_VERIFIED;
4. SOURCE_INCOMPLETE and DECODER_UNSUPPORTED propagate without false absence;
5. coverage totals and categories are internally consistent;
6. decoder parse/decode success cannot imply semantically_verified;
7. RuntimeEvidenceBundle v2 rejects replay/trace, corpus, build or contract binding mismatch;
8. canonical serialization produces stable SHA-256 identity;
9. ImpactClosure is deterministic and transitive;
10. changed evidence invalidates dependent claims/contracts/scenarios;
11. existing ReplayEvidenceBundle v1 remains readable;
12. existing Phase 1 and Phase 2 tests remain green;
13. acceptance run is repeatable twice from a clean exact-SHA checkout.

## Next checkpoints (do not fold into VNX-K001)

VNX-K002 — Differential Oracle Engine + discrepancy objects.
VNX-K003 — Discrepancy -> Evidence Trace down to source offset/evidence/hypothesis.
VNX-K004 — Universal IR field-level evidence/uncertainty + round-trip equivalence classes.
VNX-K005 — Cross-Game Decoder Laboratory 2.0: SUPPORTED/REFUTED/GAME_SPECIFIC.
VNX-K006 — Hypothesis/Falsification Engine 2.0.
VNX-K007 — Reproducibility Envelope integration.
VNX-K008 — Active Knowledge Graph dependency/impact queries.
VNX-K009 — Autonomous Reconstruction Loop 2.0.

## Pipeline target

`CACHE -> OBSERVE -> CLAIM -> FALSIFY -> DIFF -> IMPACT -> FAST -> VERIFY -> REPLAY -> ATTEST -> BUILD -> CANDIDATE`

The Orchestrator chooses the minimum required path; stages are not mandatory when irrelevant.

## Main-PC continuation

1. Fetch this branch and verify HEAD/base relationship.
2. Create a clean local worktree for VNX-K001.
3. Run existing Phase 1 + Phase 2 acceptance before modification and preserve receipts.
4. Implement A-E in small commits with tests.
5. Run targeted tests after each primitive.
6. Run full test suite twice.
7. Run Phase 1 acceptance unchanged.
8. Run Phase 2 acceptance against the exact candidate SHA.
9. Produce a VNX-K001 attestation/receipt; do not mark VERIFIED until the exact-SHA clean run passes.
10. Only then open VNX-K002.

## Exclusions

No game-specific decoder implementation, no corpus mutation, no GitHub Actions dependency, no Orchestrator production-main mutation, no broad refactor unrelated to VNX-K001, and no claim that this handoff itself constitutes runtime verification.
