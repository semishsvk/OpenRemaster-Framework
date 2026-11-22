# ORF SourceFreshnessGuard.v1 — historical R14 source versus live owner observation

**Status: SOURCE_CLASSIFICATION_SOFTWARE_PASS / OWNER_AUTHORITY_HOLD.** This is a deliberately non-authorizing **read-only review contract**. It never starts jobs, signs a lease, installs a gateway policy, changes R14, modifies original game data, or invokes an owner backend.

## Pinned evidence and scope

- Parent: M006 contract-only draft PR #13, SHA `406b7a6153aa73eb8cdffba62ea97c531b2354e4`.
- Original R14 pilot: `ORF-OWNER-MODE-HARDENING-20261013-r14`, SHA-256 `9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865`, **immutable and untouched**.
- Pilot contains exactly **62** historical SHA-256 entries under `F:\Remaster Framework`. Of these, **61** are immutables for this review and one is the explicitly classified **mutable observation**:
  `F:\Remaster Framework\orchestrator\control-plane\state\interactive-runtime-owner-v12.json`.
- Historical frozen hash of that live path: `f4496513109a23802e6a65ee959f28f71e5db189c8c4518b554cd19c86ef766e`.
- No other path is automatically reclassified as mutable. Unexpected schema, source-set change, immutable hash mismatch, path traversal, capture race or invalid metadata fail closed.

## Trust boundaries

`parse_pinned_r14_pilot(pilot_bytes)` verifies **exact sealed R14 bytes** by SHA-256 and checks schema/status/source-count. `review_sealed_r14_pilot` consumes a captured **hash-only** structure: two SHA-256 readings plus byte size for each listed path, with explicitly bounded capture timestamps. It must never accept the contents of an owner token, nonce, session, job payload, signature or self-asserted readiness.

A complete, hash-matching static source set permits only the diagnostic statement `immutable_matched_count=61`. The live owner-state hash is compared with the historical pilot and captured twice for race detection. Any legitimate change to this state remains **`LIVE_OWNER_OBSERVATION_CHANGED_UNATTESTED_HOLD`**, not acceptance. Stable bytes and recently claimed time do not establish who currently holds an owner lease, whether a global nonce was spent, or whether the observation is even authenticated.

`classify_untrusted_hash_capture` exists for pure synthetic tests; it **cannot** authenticate the integrity of hashes supplied by the caller. The sealed wrapper verifies pilot provenance only, not the capturing process. All responses have `status=SOURCE_FRESHNESS_REVIEW_ONLY_HOLD`, `dispatch_authorized=false`, `worker_execution_authorized=false`, `current_owner_authority_verified=false`, and `legacy_r14_full_acceptance_reclassified_as_pass=false`.

## Existing R14 evidence remains a historical HOLD

The full original R14 suite on HomePC ran **150 tests: 149 PASS / 1 FAIL** because the original frozen pilot treats the changing owner observation as immutable. This failure is not suppressed, edited, or relabelled. Separate R14 anchor/integration tests passed; this is not a new R14 acceptance.

New additive evidence from a HomePC read-only double-hash of the 62 original files on 2026-10-14:
- Exact sealed pilot SHA-256 PASS
- 61/61 statically classified immutable SHA-256 PASS
- Live observation changed since the frozen baseline but was stable across one read pair
- Negative in-memory mutation of a static SHA correctly yields `IMMUTABLE_SOURCE_DRIFT_OR_RACE_HOLD`
- No raw owner JSON, tokens or signer credentials persisted
- Read-only evidence: `R14_SOURCE_FRESHNESS_REAL_READONLY_SNAPSHOT_20261014.json`, SHA-256 `f47a6721f577710309bb9e47fa3e33a6c46919505ae17cd03c3b858ac8224ee5`.

## Test commands

Public synthetic test only (Windows or CI):

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q tests/test_source_freshness_guard_v1.py
```

To reproduce HomePC-only original R14 evidence, use an independently authorized read-only fixture runner. That runner is deliberately **not included** in this public commit because it requires locally installed R14 source and the mutable original observation, neither of which should be uploaded automatically.

## Next P0 gates

1. Independent owner/writer review of **who** is updating the live owner JSON and source/nonce/epoch binding; a timestamp/hash is not authority.
2. New schema with separately signed, **current** owner-state observation and immutable-source pins, preserving historical R13/R14 pilots byte-for-byte. Must enforce source provenance and expiring witness/current-head with anti-replay.
3. Explicit R14 HMAC ↔ M005 Ed25519 domain mapping for source, work scope, owner epoch, receipt and corpus; no lossy hash conversions or status laundering.
4. Global durable CAS, receiver ACK, anti-downgrade V1/V2, native worker-side fencing per side effect and owner-approved migration before production.
5. Exact SHA-bound HomePC or GitHub CI test evidence; complete Phase 2/game-fidelity checks are separate.

**Always: `PRODUCTION_DISPATCH=BLOCKED`; `R14_FROZEN_PILOT=HISTORICAL_SOURCE_FRESHNESS_HOLD`.**
