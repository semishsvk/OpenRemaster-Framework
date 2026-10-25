# ORCH-M008 — OwnerObservationAttestation.v1

**Status: SYNTHETIC_SIGNATURE_PASS / EXTERNAL_CURRENT_OWNER_AUTHORITY_HOLD / PRODUCTION_DISPATCH_BLOCKED.**

Pure offline, read-only Ed25519 evidence verification. No signing key, network client, database, native worker, live owner lease, queue writer or game source access exists in this module.

## Immutable prerequisites

- Pinned parent: M007 SourceFreshnessGuard.v1, commit `d555dd5135360e1b85e5273d4b7b5c8da7b034f3` (draft PR #15).
- Local R14 source is **not uploaded**. Frozen pilot SHA-256 `9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865` remains unchanged.
- Runtime library: `src/openremaster/m008_owner_observation_attestation.py`.
- Python fixtures: `tests/test_m008_owner_observation_attestation.py`, `tests/test_m008_wire_schemas.py`.
- Draft2020-12 shape schemas: `contracts/orch-m008/owner-observation-attestation-v1.schema.json` and `contracts/orch-m008/pinned-owner-highwater-v1.schema.json`.

## Signed, explicitly non-authorizing claim

`ORF-M008.OwnerObservationAttestation.v1` uses an exact-field envelope and a distinct Ed25519 signing context `OpenRemaster|OwnerObservationAttestation|v1\0`. The signed bytes use stable Python sorted-key compact UTF-8 JSON, not RFC 8785/JCS.

The signed claim binds (1) attestor, authority and registry scope, owner project/edition; (2) R14 policy HMAC record SHA-256, external R14 review anchor SHA-256, source SHA-256, canonical owner-work-scope SHA-256, original R14 string owner-epoch, fence generation, policy epoch and nonce; (3) the **actual M005 Ed25519 anchor** hash, separate 40-character Git revision and corpus SHA-256, mapped numeric owner epoch and owner ID; (4) the **entire M007 double-read hash-only capture SHA-256**, its signed finished timestamp, source-guard report SHA-256, owner-observation hash and size; and (5) challenge, signed prior high-water hash, sequence and bounded issued/expiry times.

The module invokes the unchanged `verify_detached_anchor(**m005_verified_bundle)` to check the actual M005 signature and its owner/snapshot/receipt semantics, with the **same verification clock** as M008. An M008 claim cannot be signed before the already-signed M005 input exists. It also checks the M007 double-read capture exactly (62 records, owner read-pair hash, observed timestamp, 60-second bound).

`ORF-M008.PinnedOwnerObservationHighwater.v1` contains a **caller-provided** expected authority, registry, sequence, numeric epoch and previous attestation digest. It is a replay-detection *hint*, NOT a remotely authenticated, current, rollback-proof global head. A signed mapping of R14 `owner_epoch` string to M005 numerical epoch cannot establish independent global owner authority.

### Strict output contract

On a structurally and cryptographically consistent *synthetic* candidate, return `SIGNED_CROSS_BOUND_REVIEW_NOT_CURRENT_OWNER_AUTHORITY`. Valid Ed25519 bytes and M005 signature are acknowledged, but all authorization fields stay false:

- `dispatch_authorized=false`, `worker_execution_authorized=false`;
- `externally_current_highwater_verified=false`, `challenge_single_use_verified=false`;
- `r14_owner_policy_mac_independently_verified=false`, `r14_anchor_mac_independently_verified=false`;
- `source_guard_report_independently_authenticated=false`, `source_capture_authenticated_by_independent_reader=false`;
- `numeric_epoch_to_r14_epoch_id_trusted_mapping_verified=false`, `global_owner_scope_authority_verified=false`;
- `native_cas_receipt_provenance_verified=false`, `production_native_worker_fencing_verified=false`.

`next_highwater_proposal_only` is NEVER a durable current-head commit. No code path can grant a worker the right to execute.

## Tests and provenance

On isolated HomePC Windows Python 3.14.3, pytest 9.0.2, cryptography 46.0.4, jsonschema 4.26.0 and rfc3339-validator 0.1.4:

- Offline M008 Ed25519 binding and negative cases include changed signed fields, forged keys, malformed captures and timestamps, stale high-water, wrong owner scope, replay, modified M005 signature and incorrect prior heads.
- Wire-schema tests check exact fields, signed time formats and strict JSON type/pattern constraints. **Schema validity is not cryptographic verification**.
- A separate HomePC-only test imports the original unchanged local R14 software (synthetic fixture keys only). No private test key, production signer, source file or owner-state JSON is shipped in this public PR.
- A combined M001–M008 synthetic suite is run on the user-authorized isolated HomePC runner, NOT GitHub Actions.

## Mandatory next steps before production

1. Deploy an independently maintained **trusted current high-water authority**, not an in-process fake callback. It needs rollback-resistant monotonic epochs/sequence, authenticated live lookups, signer key lifecycle and revocation, trusted time, consumed challenges and partition/crash recovery.
2. Obtain a separately signed owner work-scope resolver and **verified** R14 string epoch ↔ M005 numeric fencing mapping, with canonical job/attempt/source/corpus equivalence.
3. Independently verify real R14 policy/anchor HMAC and native owner CAS receipt provenance. Ed25519 review keys cannot automatically supersede existing R14 trust domains.
4. Implement gateway V1/V2 anti-downgrade, receiver ACK and worker-side epoch enforcement at **every side effect**, with max three heavy worker slots and one writer per project.
5. Preserve R14 historical original pilot at 149 PASS / 1 FAIL from the mutable owner observation; SourceFreshnessGuard classifies but does **not** amend or relabel that historical record.
6. Require exact-SHA CI, owner-approved commissioning and separate game-specific runtime/frame/audio/replay fidelity gates.

**PRODUCTION_DISPATCH=BLOCKED. No merge into `main`, no native worker job, no HomePC agent/gateway activation, no corpus mutation.**
