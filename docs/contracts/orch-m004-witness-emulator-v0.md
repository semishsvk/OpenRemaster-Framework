# ORCH-M004 — Forward-only witness/recovery emulator v0

**Status: SYNTHETIC_LAB_PASS / PRODUCTION_BLOCKED.** This implementation is a **two-store protocol experiment**, not a trusted witness, production fencing authority, launcher, or change to the canonical OpenRemaster runtime.

## Pinned inputs and ownership

- Parent: M003 `ff9b87512b6bfbd1393e8089546b988b4ea778dc` (draft PR #8).
- New isolated module: `src/openremaster/m004_witness_lab.py`.
- No modification to `main`, the Code Vault, M001–M003 implementations, or recovered source. No HomePC access, worker startup, credential use, commercial game data or Work.
- The test's SQLite owner-store adapter implements the documented M003 `snapshot/apply` interface. A separate optional smoke test imports **actual** M003 `CASLab` when the package is present; standalone tests skip this one test rather than fabricate or claim to have run actual M003 locally.

## Protocol — explicitly **not** authorization

Two independent **SQLite files on one disposable host** emulate (A) owner CAS and (B) a witness that records a proposed state transition. The witness emulator stores a `PREPARED` intent and a `COMMITTED` revision/epoch/content hash, each authenticated with a **process-local symmetric HMAC**. This prevents unnoticed local record edits without the test key; it **does not** make the witness independent, non-rollbackable, authenticated across systems or authoritative.

1. The owner and witness begin at the exact same sealed genesis `(revision=0, owner_epoch=0, content hash)`.
2. Coordinator reads owner and witness and only proceeds if stable and exact-match.
3. Witness transaction persists one signed `PREPARED(before → target)` transition. Other proposals are blocked while pending.
4. M003-shaped owner CAS applies `BEGIN IMMEDIATE` and a conditional owner state+receipt transaction. The witness is **not** the owner authority.
5. Witness **forward-finalizes** only if the observed owner record matches the exact committed target revision, epoch and content hash.
6. On recovery: stable + matching DB → `STABLE_LAB_ONLY`; pending + old DB → `PENDING_WITH_OLD_DB_BLOCKED` (**never silently abort**); pending + new exact DB → forward-finalization; any divergence → **BLOCKED**.
7. Every output has `dispatch_authorized:false`. Even a MAC-valid two-store match is not owner authorization, proof of process execution, or semantic validation of game evidence.

## Failure behavior tested

- Synthetic interruptions: after witness prepare, after owner DB commit, and after witness finalization.
- Two concurrent coordinators: at most one proposal can pass the witness PREPARED gate.
- Tampered witness committed state, modified pending intent or MAC, forged finalization ticket, replayed ticket, secret rotation/loss: **fail closed**.
- Restored **owner-only** or **witness-only** database: divergence **blocks** progress.
- Restoring **both databases** to a previously valid snapshot: **not detected**. A symmetric MAC proves integrity at a given point, **not monotonic freshness**, and an attacker possessing the MAC key can forge records.
- A prepared intent with old DB intentionally remains blocked even if it may never have been committed. This is a **safety-over-liveness** decision requiring a separately verified cancellation/abort/fencing protocol in a later milestone.
- The coordinator does **not** independently verify the owner's persisted idempotency receipt or protect the gap between reading the owner state and witness finalization. It must not be used as a full recovery oracle.

## Reproduction

```bash
PYTHONPATH=src python -m pytest -q tests/test_m004_witness_lab.py
```

Isolated sandbox on 2026-10-13: Python 3.13.5 / SQLite 3.46.1 / pytest 9.0.2: **38 passed, 1 skipped** (the actual M003 smoke test was not locally installed). No full Framework Phase 2 acceptance or GitHub-hosted CI PASS was established.

## Production blockers (non-negotiable)

- Reconcile unpublished HomePC K003/K004/R11–R13 code and single-writer policy against exact SHAs before any integration.
- Use an **actually independent** trusted, append-only/monotonic witness outside the DB and rollback domain: signed attestations with key rotation, authenticated caller identities, denial of stale epoch, anti-replay and authoritative time, backed by an independently audited infrastructure.
- Design a provably crash-safe prepare/commit/abort protocol; external witness and DB cannot become transactionally atomic by putting both SQLite files on one host. Prove the locked recovery path cannot finalize a forged DB target without a validated owner-CAS receipt.
- Workers must independently enforce fencing on **every side effect**, not merely in control-plane code. Maintain a maximum of three heavy slots and one writer per authorized namespace.
- Validate multi-host partitions, out-of-order acknowledgements, stale owners after restart, lost keys, witness rollback, disk corruption and multi-process races with negative fixtures and **actual SHA-bound GitHub Actions CI**.
- Do not promote M004 or unlock production dispatch while GitHub Actions issue #6 or safety issue #5 remains unresolved.

**Always**: `PRODUCTION_DISPATCH=BLOCKED`; `HOMEPC_NOT_CONTACTED`; `REAL_FIDELITY_NOT_TESTED`.
