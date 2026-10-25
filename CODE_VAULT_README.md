# OpenRemaster Framework + Orchestrator — Remote Code Vault

Snapshot: 2026-10-13. **ARCHIVED / UNVALIDATED — NOT A PRODUCTION BRANCH.**

This branch is the single GitHub location for **all framework and orchestrator source code currently recoverable from the three verified GitHub inputs**, without overwriting `main` or individual source branches. It is NOT a statement that every local HomePC file has been uploaded.

## Layout and authority

- `src/`, `scripts/`, `tests/`, `docs/`, `portfolio/`, `evidence/`: canonical Framework `main` plus isolated M001 draft changes, exactly as in commit `ec415f36e86a74cf7e3d651569a437eea0a25585`.
- `contracts/remote-control/v1/`, `src/openremaster/remote_control.py`, related test and workflow: M001 **draft**, not approved or deployed.
- `recovered/2026-10-09/`: complete **quarantined** recovery snapshot of 376 project-authored code files and its original 3 metadata files, grafted using the existing immutable Git tree `67ea3de8f662547d08d708c278a11b3c34f30d54` from `4326d2c184b6865743bb20f8c89e745bd110fd09`. **Never import, execute, ship, or auto-promote this directory until audited**.
- `CODE_VAULT_MANIFEST.json`: per-file inventory with Git blob identities; recovery SHA-256 hashes are *recorded assertions* from the original manifest, not independently rehashed in this task.

## Pinned sources

- `main`: `8195f3754219b487deb0947a29d8af6cfe1babc9` (frozen baseline / no mutation).
- `remote-control/m001-contracts-20261013`: `ec415f36e86a74cf7e3d651569a437eea0a25585` (draft PR #2 remains separate).
- `consolidation/code-only-20261009`: `4326d2c184b6865743bb20f8c89e745bd110fd09` (original recovery branch remains separate).
- The vault commit has the M001 and recovery commits as Git parents; their histories remain reachable.

## Safe continuation protocol

1. Use the **immutable commit SHA** of this vault snapshot as the reference. Branch names may move; never trust branch name alone.
2. New changes go on fresh feature branches based on this vault **only after** checking who owns the affected paths; for Framework-only production changes, continue from the appropriate canonical branch instead.
3. Preserve `recovered/` read-only until source SHA-256/provenance, dependency, licensing/secrets review, and game-specific writer ownership have been checked. No bulk module promotion or automatic merge.
4. Do not include original commercial game binaries, media/capture assets, credentials, signed URLs, or machine-local queues in GitHub.
5. Run remote-only static and synthetic checks separately from exact-SHA local acceptance and real runtime fidelity. **No GPU, DOS, game/runtime or Phase 2 acceptance claim is made here.**
6. Reconcile unpublished HomePC code (especially K003/K004 and R11–R13) against this index when authorized access is available; never assume the vault has it.
7. Known existing defect to address in a separate small fix: `scripts/phase2_acceptance.py` uses `argparse` without importing it. Preserve this exact source snapshot rather than silently modifying it during archival consolidation.

## Next steps

1. Verify this vault's Git tree against `CODE_VAULT_MANIFEST.json` (path, mode, blob SHA and size).
2. Establish a green CI result at an exact commit for M001 and address the Phase 2 acceptance runner defect in a narrow reviewed patch.
3. Classify recovered modules by owner, dependency and applicable project contract; promote only isolated proven changes.
4. Continue native agent / gateway / owner registry integration only after local-only versions are reconciled. No live dispatch until signed admission, durable anti-replay and fencing are independently validated.
