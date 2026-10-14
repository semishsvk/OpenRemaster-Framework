# ORCH-M011 — Authenticated Remote Recovery Review Contract v1

**Status: SIGNED RECEIPT LABORATORY / DURABLE LOCAL REVIEW PASS / EXTERNAL AUTHORITY HOLD / PRODUCTION DISPATCH BLOCKED.**

**M011 is not a remote service, native job launcher, active owner lease, or independently trusted current-head authority.** It verifies Ed25519 signatures on recovery *claims*, then records signed claims in a LOCAL SQLite transaction with the M010 diagnostic head. Valid review signatures do not prove the remote head is current, that a nonce was consumed globally, that the signer key has not since been revoked, or that a worker has permission to execute.

## Exact base

- Stacked on immutable M010 lab draft PR #20: Git SHA `34b37a6ebfde6ab16d29189660b6720ebf79b1db`.
- M010 checkpoint on isolated HomePC: SHA256 `52bb367e867d1389966a1f39b7a10fc82510d3464c34b8eba6fbe1686b211417`.
- The 35 M010 Git blob hashes and source bytes are pinned/read-only. No M010 code or original R14 source is changed by M011.
- No production owner registry, gateway, native worker, K003 job, live nonce ledger, game corpus or private key is touched.

## Two independent operations

**Step A — PLAN**: `SignedRecoveryJournal.plan_probe` requires an existing PREPARED/UNKNOWN M010 operation and atomically persists one local recovery probe before any possible remote communication. The plan stores probe ID, one-time *locally unique* challenge, request SHA256, **pre-agreed remote operation SHA256**, **pre-agreed M009 signed-head receipt SHA256**, and the minimum expected trust generation. The original M010 operation becomes UNKNOWN **in the same SQLite transaction**. Reissuing a different probe for the same operation is blocked. `mark_partition` keeps UNKNOWN, never guesses failure or commit.

**Step B — VERIFY AND RECORD**: `verify_signed_recovery_receipt` verifies a domain-separated Ed25519 receipt (`OpenRemaster|M011-SignedRemoteRecovery|v1` followed by a zero byte). Every signed byte binds authority and key IDs, exact operation/namespace/probe/challenge/request, prior/candidate/resulting heads, monotonic sequence/epoch/fence, remote operation identifier, prior M009 head receipt hash, current caller-pinned trust generation, issued/expiry timestamps and a decision of exactly COMMITTED or REJECTED. UNKNOWN is never a signed affirmative result.

The public trust view (`PinnedRecoveryTrust`) is explicit caller-supplied, expiring and key-ID/revocation bound. M011 **cannot independently prove** that this trust snapshot is the latest remote generation. A valid Ed25519 signature proves only that the holder of the pinned private key signed the exact payload.

**Same local transaction**: `apply_signed_result` starts SQLite BEGIN IMMEDIATE and rereads the preplanned probe, M010 operation and M010 head. It rejects mismatched IDs, hashes, challenge, counters, stale local head, final operations or trust generation downgrade. A review-valid COMMITTED claim moves the *local diagnostic* M010 head and records receipt digest; a review-valid REJECTED claim keeps the local head and marks the local operation rejected. Both update M011 probe final state, local signer key-material history, monotonic trust generation and revocation tombstones in that same SQLite transaction. Neither modifies any remote authority.

**All status outputs stay non-authorizing**: `external_current_head_verified=false`, `remote_commit_signature_is_authoritative_for_native_jobs=false`, `remote_challenge_single_use_verified=false`, `local_rollback_resistance_proven=false`, `native_worker_dispatch_authorized=false`, `worker_execution_authorized=false`.

## Explicit trust and durability gaps

- A caller can pin an old but internally valid trust/public-key snapshot and submit an old valid signed receipt; no authenticated current-generation remote query is implemented.
- M009 remote-head receipt hash and remote-operation hash are pinned to the previously stored local plan, but M011 **does not separately validate the actual M009 signature or its external freshness**. Those two SHA bindings must NOT be treated as a chain-of-trust proof.
- Local SQLite WAL and synchronous FULL support bounded transactional recovery only. They are **not** external rollback-resistant monotonic memory, and cannot survive a privileged full database restore as a proof of currency; the negative test explicitly demonstrates this.
- M010 remains a standalone, directly accessible lab. M011 cannot prevent another program from calling M010's old caller-supplied COMMIT_CONFIRMED review API. A production interface must prohibit such bypass at the native receiver/owner boundary.
- No remote ACK transport, owner-work-scope issuer, R14 string epoch-to-numeric generation authority, global atomic CAS, trusted time, consumed nonce, signer revocation service, side-effect fencing, native worker admission or genuine gameplay-fidelity check exists here.

## Crash and replay tests

Test-only failure windows: BEFORE_PROBE_COMMIT, AFTER_PROBE_COMMIT, BEFORE_SIGNED_RESULT_COMMIT, AFTER_SIGNED_RESULT_COMMIT. Dedicated child Python processes call os._exit at these points, then reopen only a pytest-owned SQLite database and validate PRAGMA quick_check plus expected state. No worker/job launch or production side effects. Additional tests exercise replay, competing signed results, incomplete/expired signatures, signer rotation and key-ID rebind prevention, revocation tombstones, stale trust-generation, malformed signed fields and deliberate full-DB rollback.

Strict Draft 2020-12 JSON Schema validates the 22 signed fields but not Ed25519 signature/semantic relations. JSON Schema format=date-time requires pinned rfc3339-validator (without the optional backend jsonschema may silently accept malformed timestamps). Schema validity is not execution authority.

## Reproduction

Run only the isolated synthetic modules from the pinned M011 source root (not from a production project):

```bash
PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_m011_signed_recovery.py tests/test_m011_wire_schema.py
```

Dependencies: `pytest==8.3.5 jsonschema==4.23.0 rfc3339-validator==0.1.4 cryptography==46.0.4`. A read-only workflow defines the full selected M001–M011 synthetic chain for a future enabled GitHub Actions runner; user-approved HomePC is the current isolated test runner.

## Before a production integration could even be proposed

1. An independently managed authenticated **external current-head + signed remote recovery** service with rollback-resistant state, cross-host atomic compare-and-swap, real nonce consumption and durable query/response idempotency.
2. Independent signed owner-work-scope, numeric epoch and R14 canonical string-epoch binding. Verify actual M009 signed receipt and current revocation generation against a separate source of trust.
3. Native receiver ACK and worker-side fencing at **every side effect**, including cross-crash recovery without duplicate execution.
4. Explicit owner-approved versioned activation/rollback, negative-first live canary, maximum three heavy slots and one authorized writer per project.
5. Independent game-specific original frame/audio/replay fidelity. Historic R14 source pilot 149 PASS / 1 FAIL is preserved, not relabeled by lab tests.

**PRODUCTION_DISPATCH=BLOCKED. No main merge, no active gateway or owner state changes, no native jobs or proprietary corpus access.**
