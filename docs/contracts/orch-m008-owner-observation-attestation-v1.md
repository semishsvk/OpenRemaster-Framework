# ORF-M008 OwnerObservationAttestation.v1

**Status: OFFLINE DUAL-SIGNATURE CONTRACT / REVIEW_ONLY / PRODUCTION_DISPATCH_BLOCKED.**

This proposal adds a cryptographic *structural* link between (1) an Ed25519-signed owner observation and (2) a separately Ed25519-signed monotonic-head **claim**. It is not an external owner provider, signing service, anti-rollback register, native execution authority or source-fidelity oracle.

## Pinned ancestry

- Parent: SourceFreshnessGuard.v1 draft PR #15, Git commit `d555dd5135360e1b85e5273d4b7b5c8da7b034f3`, no merge to `main`.
- R14 original sealed pilot SHA-256: `9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865`.
- R14 status remains **149 PASS / 1 FAIL** in the original frozen suite because one of its 62 historical input hashes represents a **mutable live owner observation**.
- SourceFreshnessGuard.v1 on real R14 pilot: 61/61 immutable inputs match, live observation changed but remained stable during a bounded two-read sample. This is **not current owner authority**.

## Two distinct signing envelopes

**OwnerObservationSigned.v1**: detached Ed25519 signature over a strictly versioned, domain-separated exact JSON representation containing project namespace, owner/job/attempt/worker, R14-style **string** owner epoch label, separate positive integer proposed fencing generation, trusted-owner-work-scope SHA-256, native source SHA-256, **separate** 40-hex Git revision, corpus SHA-256, request SHA-256, observed hash-only owner-state SHA-256, sealed R14 pilot SHA-256, bounded UTC timestamp interval and a replay challenge.

**ExternalMonotonicHeadSigned.v1**: an independently keyed signature over authority/namespace, prior head SHA-256, sequence and fencing proposal, the hash of the **entire signed owner envelope**, the same work scope/epoch label/corpus/Git revision/observation/request/challenge, and a <=60 second UTC window.

Both signatures use **distinct domain separators** and require two distinct pinned public keys. The *caller* supplies those keys, the prior external checkpoint, independent expectations, challenge and clock; this module cannot prove the caller is trusted or that the alleged head is current. A stale signed bundle **and an equally stale caller-supplied pinned head** can still pass structural consistency. The negative tests demonstrate this intentionally.

The guarded positive result is:
`TWO_SIGNATURES_STRUCTURALLY_VALID_NOT_CURRENT_AUTHORITY`.
It includes a `next_head_proposal_only` and **all** of these hard-coded false: `current_external_highwater_verified`, `owner_epoch_cross_domain_mapped`, `owner_work_scope_resolver_authenticated`, `external_challenge_uniqueness_verified`, `durable_nonce_spend_verified`, `owner_cas_receipt_verified`, `worker_side_fence_verified`, `production_owner_authorized`, `dispatch_authorized`, `worker_execution_authorized`.

An M007 SourceFreshness review is checked for expected source-pilot scope, 61 matching immutable sources, no drift and owner hash equality, but **its origin is still a caller assertion** and `source_review_origin_authenticated=false`. The module never opens the live owner JSON and must never transmit tokens/sessions/keys.

## Strict negative fixtures

Checks cover owner/head signature mutation or forgery, wrong signer/key role, same key used for both roles, truncated or noncanonical signature, changed scope/job/attempt, changed source/corpus/observation hash, invalid or mismatched epoch, stale/split sequence, head fork, bad challenge, invalid and swapped trust domains, expired/future timestamps, forged M007 review flags, partition/timeout/stale network reports and replayed old signed checkpoint.

## User-authorized HomePC evidence

- Python 3.14.3 / `cryptography==46.0.4` / `pytest==9.0.2` in a separate venv already established for OpenRemaster's bounded synthetic CI.
- M008 alone: **138/138 PASS** (no original runtime, no production signing keys).
- Full M001–M008 exact-parent copied synthetic suite on HomePC: **455 passed, 0 failed, 0 skipped, exit 0** in 7.64s. The new commit's four Git blob identities must be verified independently before attaching the SHA-bound checkpoint.
- Additional HomePC-only genuine copied-R14/M008 crosswalk: **7 passed, 0 failed**. This test file imports unpublished local R14 test fixtures and is intentionally not distributed in this public contract-only PR.
- Test signing keys are ephemeral Ed25519 objects created in memory and are never committed or used by live R14.

## Production gate (NOT solved)

1. Independent, mutually authenticated **current external high-water provider**, with rollback protection outside HomePC and owner DB restore domain.
2. Uniquely consumed challenge/nonce ledger, signed revocation/key rotation, trusted time, monotonic sequence/epoch and partition-safe recovery.
3. An authorized source-provenance resolver binding R14 work-scope string epoch to a separately assigned numerical fence; exact source SHA-256, Git commit and corpus SHA remain **different** identities.
4. Independently verified **durable native owner CAS receipt** and receiver ACK. Enforce owner fence at **every** K003/native worker side effect and in the gateway; no metadata stripping V1→V2.
5. Owner/writer review of R11–R14; preserve frozen checkpoints byte-for-byte; no automatic live owner takeover or migration.
6. Exact-SHA synthetic CI pass is **not** Phase 2 acceptance or original-game fidelity.

**ALWAYS `PRODUCTION_DISPATCH=BLOCKED`. Draft-only, contract-only: do not merge or deploy automatically.**
