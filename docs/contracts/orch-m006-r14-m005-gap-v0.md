# ORCH-M006 — R14 ↔ M005 trust-boundary crosswalk (v0)

**Status: SYNTHETIC CONTRACT PASS / CROSS-DOMAIN AUTHORITY HOLD.**

This is a read-only, deterministic **gap detector**, not a protocol adapter, R14 key verifier, trusted current-anchor client, owner registry, execution gate, or acceptance oracle. `diagnose_review_gap` only inspects *already independently produced review data* and returns `HOLD_INCOMPATIBLE_TRUST_DOMAINS`. It **never** returns `dispatch_authorized:true`.

## Pinned inputs and immutability

- GitHub M001–M005 plus RFC3339 integrated base: `92bbd348c905afbd00bbe28a523d19928080125f` (draft PR #12, no merge).
- Local HomePC R14 module: `F:\Remaster Framework\orchestrator\native-owner-mode-registry-hardened-v2`; source-only R14, **production NOT wired**.
- R14 `r14_core.py` SHA-256: `11960a4be1a83508f00f45cb83401c00ed8235b377336a8365a630808c9b9f33`.
- R14 `rollback_anchor.py` SHA-256: `681437581e469dc38d19c6febd85fab2178945c103dbaa9f98aa8bc80c758516`.
- R14 frozen pilot SHA-256: `9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865`.
- Existing M005 Ed25519 verifier blob SHA: `3f3cb86b1339ea33316252d24ee4769c45f6521b`.
- R14 source and schemas have not been uploaded to GitHub and remain independently owned.

## Incompatible trust domains (no implicit conversion)

| R14 local source | M005 contract | Missing bridge |
|---|---|---|
| HMAC signed R14 external anchor, review-only audience | Ed25519 signed M005 anchor, distinct signing domain | Explicit independent authority and verified cross-signature/attestation |
| `owner_epoch` is a signed **identifier string** in the R14 owner policy | `owner_epoch` is a **monotonic integer** | Independently authorized, rollback-resistant epoch mapping |
| Signed `owner_work_scope_sha256` (64 hex) | M005 namespace and request/owner identifiers | Trusted owner-scope resolver and same-work binding |
| R14 `source_sha256` (64 hex) | M005 `source_revision` (40-hex Git SHA) and corpus SHA | Source/corpus provenance crosswalk, not truncation |
| R14 anchor hashes registry event chain and mode count | M005 anchor hashes owner snapshot and M003 lab receipt | Verified owner-CAS receipt and chain inclusion proof |
| R14 test callback claims externally current HMAC anchor | M005 accepts caller-pinned highwater; explicitly marks freshness false | Real independent current-head service with antirollback, anti-replay and revocation |
| Host-local SQLite uniqueness and V1/V2 exclusion | M003/M004 SQLite research models | Actual global atomic CAS, native ACK and worker-side fencing |

The M006 implementation **does not validate the R14 HMAC or M005 Ed25519 signature itself**. Even two independently positive synthetic reviews are not cross-domain proof. All fake signatures and callbacks in the HomePC test suite remain test-only.

## Actual HomePC evidence, 2026-10-14

- M001–M005 plus M006 synthetic tests in an isolated copied tree: **262 PASSED, 0 FAILED, 0 SKIPPED**, exit 0, Python 3.14.3 on HomePC. R14 was not imported by these public synthetic tests.
- Separate HomePC-only test importing **actual unchanged R14 copied modules** and the M005 signer/verifier: **39 PASSED, 0 FAILED**. The 39 include **25 original R14 rollback-anchor tests auto-collected** and **14 additional R14/M005 cross-domain tests**.
- Original full R14 isolated mirror: **150 tests, 149 PASS, 1 FAIL**, because one of the 62 frozen pilot SHA references points to a *mutable runtime owner observation*. Exact SHA reread: **61/62 match**. Do not rewrite the frozen pilot and do not label R14 fully reaccepted.
- Live observation path: `F:\Remaster Framework\orchestrator\control-plane\state\interactive-runtime-owner-v12.json`. Frozen SHA `f4496513109a23802e6a65ee959f28f71e5db189c8c4518b554cd19c86ef766e`; observed SHA `671658da80a036fdde680d140c3752ad12060f5c0a113098233600dce5f6bb34` at the read-only audit. Its provenance/freshness requires independent owner review.
- R14 mirror: **18/18 Python + 8/8 schema/evidence JSON SHA-256 equal** to installed originals. R14 original sources, native gateway/agent, owner leases, game corpora and runtime jobs were not changed.

## Release constraints

1. Never promote a boolean PASS from either system into a trusted execution admission.
2. Independently authenticate owner-work scope, complete source/corpus identity, global nonce spend and numerical fencing generation.
3. Independently validate native-owner CAS receipts, signed current external monotonic witness and receiver ACK; check every side effect at the native worker.
4. Separate mutable owner observation freshness from immutable source SHA acceptance. A new reviewed, evidence-bound pilot must reconcile the single drift without rewriting frozen R14 evidence.
5. Preserve single-writer per project, at most three heavy slots, immutable game source; no job execution or home PC deployment through this PR.
6. GitHub Actions remains 0 runs; user-authorized HomePC was used only for the scoped synthetic suites. Full Framework Phase 1/2 acceptance and game runtime fidelity are **not** established.

**Gate remains `PRODUCTION_DISPATCH=BLOCKED`, `R14_FROZEN_PILOT=SOURCE_FRESHNESS_HOLD`, `M006_CROSS_DOMAIN_TRUST=HOLD`.**
