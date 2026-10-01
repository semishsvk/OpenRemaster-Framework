# Portfolio Consolidation Contract

This contract makes project consolidation fail closed.

## Authority boundaries

- Original game corpora are immutable external inputs and MUST NOT be committed to Git.
- GitHub is a synchronization/review/checkpoint surface, not the authority for original game bytes.
- A remote repository or branch does not prove that local work is synchronized.
- Missing information is `UNKNOWN`, never implicitly clean, current, verified, or absent.

## Required local preflight

Before any project synchronization, capture: repository/worktree path, branch, HEAD, upstream, porcelain status, staged/unstaged/untracked paths, worktrees, remotes, task-relevant input paths, and hashes where fidelity/provenance requires them.

Classify discovered work as `VERIFIED`, `WIP`, `EXPERIMENTAL`, or `STALE_UNKNOWN`. Preserve bytes before reconciliation.

## Mutation gates

No reset, clean, force push, history rewrite, bulk merge, or deletion during discovery. GitHub writes are serialized under a single-writer lease. A project may move from `LOCAL_STATE_REQUIRED` to sync planning only after its local snapshot is captured.

## Consolidation result

Each project produces an immutable occurrence/checkpoint record linking content identity, provenance, validation attestations, source/toolchain lineage, pending tasks, and next action. Verification is a claim under a validation contract; it is not mutable state embedded in artifact identity.
