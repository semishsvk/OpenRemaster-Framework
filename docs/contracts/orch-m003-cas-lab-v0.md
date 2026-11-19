# ORCH-M003 — SQLite CAS Laboratory (v0)

**Status: LAB_PASS / PRODUCTION_BLOCKED.** This is a *disposable test-only SQLite model* for the M002 structural CAS proposals. It is not an orchestrator, admission service, lease authority, source materializer, or worker. **Never use its returned values to start processes or authorize side effects.**

## Pinned authority and scope

- Parent: M002 draft `0bf891299112c1292ffbddf1aaaa596d6666fc30`. New files only. Canonical `main`, M001/M002 and the quarantined Code Vault are not modified.
- Module: `src/openremaster/m003_cas_lab.py`. Uses only Python stdlib `sqlite3` and a caller-supplied temporary database path. NO HomePC, Work, GitHub secrets, networking, game bytes, or recovered worker execution.
- Accepts M002-style proposals `ACQUIRE_PROPOSAL_ONLY`, `RENEW_PROPOSAL_ONLY`, `RELEASE_PROPOSAL_ONLY`. Validates the complete owner-state transition, bounded expiry, exact owner token (for renew/release), monotonic `store_revision` and monotonic `owner_epoch` on reacquisition.
- Uses `BEGIN IMMEDIATE`, a conditional `UPDATE WHERE revision=? AND epoch=?`, `PRAGMA synchronous=FULL` and a receipt table with unique `(namespace,idempotency_key)`. Owner state and idempotency receipt commit in one SQLite transaction.
- Every returned value includes `dispatch_authorized:false` and has only `LAB_ONLY` semantics. **A durable database write is not an authorization or trusted lease.**

## Bounded synthetic outcomes

- Concurrent competing acquirers against the same revision: exactly one SQLite CAS commit; the other is rejected.
- Duplicate key, same request digest: idempotent `REPLAYED_LAB_ONLY` after external witness reconciliation; changed request digest with same key is rejected.
- Crash before commit: SQLite rollback retains prior state and no receipt. Crash after commit before reply: state persists, but subsequent requests fail closed against the previous witness until external witness reconciliation.
- Expired owner cannot renew/release. A new acquisition increments fencing epoch; earlier owner tokens cannot mutate the new state. Missing or modified token fails closed.
- Simulated rollback of database bytes is detected **only if** a separately retained witness still has newer `revision/epoch`. An adversary able to forge or roll back the witness can defeat this lab mechanism: a negative test explicitly demonstrates that limitation.
- A hash or version field is not a signature. The test clock is caller-controlled; no trusted clock is implemented. No external write authority, corruption-resilient audit, fsync guarantee for all hardware, authorization service, or rollback-proof monotonic register is included.

## Verification

Run in an ephemeral filesystem, with only the new isolated tests:

```bash
PYTHONPATH=src python -m pytest -q tests/test_m003_cas_lab.py
```

Local execution, **2026-10-13**: Python 3.13.5, SQLite 3.46.1, pytest 9.0.2: **37 passed**, 0 failed. Source and test Git blobs are pinned in PR; GitHub Actions PASS is **not confirmed** (issue #6).

## Mandatory production gate

1. Independently reconcile unpublished K003/K004/R11–R13 implementations and ownership; do **not** replace newer local durable registry with this lab.
2. Require an authenticated, independently maintained, rollback-resistant monotonic witness/epoch and a transactional protocol safe under crash between main DB commit and witness advancement. A plain caller-supplied `(revision,epoch)` tuple does **not** satisfy this requirement.
3. Require authoritative signed ownership and time/capacity attestations, worker-side fencing for **every** side effect, durable cancellation/heartbeat, and signed evidence bytes + provenance validation.
4. Verify multi-process and cross-host races, corrupt/partial database restores, restart and disk failure semantics, and actual GitHub CI at a pinned SHA. Finally conduct explicitly admitted HomePC commissioning.
5. Until then: `PRODUCTION_DISPATCH=BLOCKED`, `FIDELITY_VERIFICATION=NOT_APPLICABLE`, `CODE_VAULT=QUARANTINED`.

Tracked in [ORCH-M002 blocker #5](https://github.com/semishsvk/OpenRemaster-Framework/issues/5) and [GitHub CI gate #6](https://github.com/semishsvk/OpenRemaster-Framework/issues/6).
