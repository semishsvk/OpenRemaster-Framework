# ORCH-M010 — Durable Current-Head Recovery Lab v0

**Status: LOCAL SYNTHETIC SOFTWARE PASS / REMOTE AUTHORITY HOLD / NATIVE DISPATCH BLOCKED.**

The M010 module is an isolated, file-backed SQLite *review journal* for M009 candidate head transitions. It is not an external current-head service, a production owner or nonce ledger, an authenticated remote receipt verifier, or a Native Worker execution adapter. Its only public result contains `external_current_head_verified: false` and `native_worker_dispatch_authorized: false`.

## Exact authority boundaries

- `initialize(scope, sequence, epoch, fence, head_digest)` pins a *caller-supplied local starting tuple*. It is not independently signed current owner state. An existing head cannot be reset or overwritten through `initialize`.
- `prepare` opens `BEGIN IMMEDIATE`, checks the expected head hash plus monotonic sequence/epoch/fence, and records a unique operation ID and challenge. If any operation already exists for that scope, new work remains blocked pending a reviewed cleanup/retention protocol. This is intentionally conservative.
- `mark_unknown` preserves an ambiguous operation on disk. **A network timeout or lost response does not imply commit or failure.** Restart reopens `PREPARED`/`UNKNOWN` without guessing.
- `reconcile` updates a *local diagnostic head only*. Its `COMMIT_CONFIRMED` argument and SHA-256 receipt digest are caller-supplied, **not cryptographically authenticated**, so success NEVER establishes external current head nor owner execution authority. `REJECTED` and `UNKNOWN` never advance the local head.
- SQLite WAL and `synchronous=FULL` may support bounded local transactional recovery when filesystem/OS/storage cooperate. They do NOT guarantee protection against physical power failure or copying/restoring the entire database, or cross-host atomic consensus. A negative test expressly demonstrates that restoring an older complete database image causes an earlier locally consistent head to reappear. External anti-rollback authority remains P0.

## Failpoint semantics and negative coverage

Test-only failure hooks are available at:

1. `BEFORE_PREPARE_COMMIT`: uncommitted operation must disappear.
2. `AFTER_PREPARE_COMMIT`: prepared operation survives lost reply.
3. `AFTER_HEAD_UPDATE_BEFORE_COMMIT`: head and operation updates roll back together.
4. `AFTER_RECONCILE_COMMIT`: both final head and receipt record survive lost reply.

Hooks raise synthetic exceptions in-process. A separate suite uses an **isolated child Python process** terminated with `os._exit` at these exact points, then reopens only its test SQLite database, checks `PRAGMA quick_check`, verifies appropriate state and ensures no authorization. No native worker, game process, K003 job, network request or production path is involved.

Other fixtures reject malformed counters, replayed challenges, conflicting local proposals, stale head/epoch/fence, duplicate confirmations, invalid receipt digests, unknown operations, corrupt ledger version and symlinked database paths. A two-connection race permits exactly one local proposal. All positive and negative outcomes retain `REVIEW_ONLY_HOLD` and `native_worker_dispatch_authorized:false`.

## Reproduction

With a Python environment that contains pytest, run this **synthetic-only** target:

```bash
PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_m010_durable_recovery.py
```

The main M001–M010 combined contract chain also needs M009-specific dependencies `jsonschema`, `rfc3339-validator`, and `cryptography` in addition to pytest. Original R14 files and test-only keys remain local on the user's HomePC and must not be uploaded automatically.

## Unresolved production P0

1. Independently operated, authenticated, rollback-resistant external **current-head** source with global CAS, one-time challenge consumption and signer revocation/rotation. Never construct it from a local SQLite receipt.
2. A cryptographically verified remote commit receipt binding operation ID, scope, challenge, parent head, candidate hash, epoch, fence, source/corpus and current key/revocation generation. M010 does **not** verify this receipt.
3. Partition-safe exact-result reconciliation, read-after-write recovery, durable remote idempotency and recovery after unknown outcomes without double execution.
4. R14 work-scope and epoch mapping with owner-controlled signing, genuine receiver ACK, original Native Worker gateway/agent hardening, and **worker-side fencing before every side effect**.
5. Independent acceptance on pinned immutable production source and game-specific original runtime fidelity. Synthetic tests, even when run on HomePC, do not commission these gates.

**Production dispatch remains BLOCKED. No merge into `main`, owner register mutation, workqueue writes, or game corpus changes.**
