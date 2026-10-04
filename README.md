# OpenRemaster Framework

Evidence-driven sidecar framework for deterministic reverse engineering, reconstruction, validation and portfolio orchestration across the OpenRemaster projects.

## Authority and safety

- Original game corpora are immutable external inputs and are never committed to Git.
- GitHub is a synchronization/review/checkpoint surface, not authority for original game bytes.
- Missing information is `UNKNOWN`; it is never implicitly clean, absent or verified.
- No `VERIFIED` claim is valid without evidence and an applicable validation contract.
- Content identity is separate from occurrence/provenance/semantic identity.
- Game-specific evidence comes first; universal contracts require cross-game validation.
- Destructive synchronization is blocked until a real local preflight exists.

## Current architecture

Phase 1 remains the frozen baseline. Current development extends the existing Phase 2/evidence architecture rather than creating a parallel system.

Key areas include:

- evidence identity, provenance and dependency invalidation;
- replay/trace and RuntimeEvidenceBundle contracts;
- decoder/coverage and negative-evidence semantics;
- impact analysis and minimum-required validation selection;
- deterministic replay and visual/runtime regression;
- portfolio checkpointing and fail-closed reconciliation.

Target pipeline:

`CACHE -> OBSERVE -> CLAIM -> FALSIFY -> DIFF -> IMPACT -> FAST -> VERIFY -> REPLAY -> ATTEST -> BUILD -> CANDIDATE`

Stages are selected by evidence/impact needs rather than run mechanically.

## Portfolio state

`portfolio/registry.json` is the current machine-readable project registry and `portfolio/tasks.json` records the remaining consistency gates.

The framework preserves intentional active-work/stable-main splits where verification is incomplete instead of forcing broad merges.

## Local acceptance

Phase 2 acceptance is local-first and does not depend on GitHub Actions:

```bash
python -m pip install -e .
python -m pip install pytest
SHA=$(git rev-parse HEAD)
python scripts/phase2_acceptance.py --expected-sha "$SHA"
```

The acceptance runner rejects SHA mismatch or a dirty worktree and executes the complete pytest suite twice before writing the SHA-bound evidence receipt.

See:

- `docs/architecture.md`
- `docs/framework-vnext-handoff.md`
- `docs/phase1-acceptance.md`
- `docs/phase2-acceptance.md`
- `docs/portfolio-consolidation-contract.md`

## Branch policy

`main` is canonical. The framework phase/vNext branches are kept aligned with `main` when their work has already been consolidated, rather than retaining stale drift.
