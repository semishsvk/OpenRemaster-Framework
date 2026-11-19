# ORCH-M005 — Detached Signed Anchor Contract v0

**Status: OFFLINE_SIGNATURE_LAB_PASS / PRODUCTION_BLOCKED.** This is a cryptographic **verifier**, not an authority service, dispatcher, durable owner store, live witness, trusted clock, or proof of current remote state. It must not be used for worker admission, native processes, game data access or fidelity claims.

## Lineage and isolation

- Pinned parent: ORCH-M004 draft commit `2fba91fc3f7a81c0a215074653fa611173cf5a08`, stacked on M003/M002/M001.
- New module `src/openremaster/m005_anchor_contract.py`; tests `tests/test_m005_anchor_contract.py`.
- Previous `main`, Code Vault, recovered workers and M001–M004 source remain immutable. No HomePC, Work, native workers, game media, or live remote API is used.
- Test keys are generated in memory with `Ed25519PrivateKey.generate()`. **Never** commit a production private signing key or credential.

## What is actually verified

`verify_detached_anchor()` accepts a **signed COMMITTED anchor**, a separately supplied/pinned high-water checkpoint, an M002-style active owner snapshot, an M003-style lab CAS receipt, expected request/source/corpus identity, a caller-asserted fresh challenge, a caller-provided clock, and a pinned Ed25519 public-key mapping.

- Strict, versioned, extra-field-denying schemas and semantic field types; SHA-256 of deterministic UTF-8 Python JSON. This is **not** RFC 8785/JCS.
- Ed25519 signature over `OpenRemaster-ORCH-M005-anchor-v0\0 || canonical_json(unsigned_anchor)` with pinned `(authority_id, key_id)` key; no local production signing key in the runtime module.
- Exact namespace, authority, worker, job, attempt, owner identity, challenge, source Git SHA, corpus SHA and request digest agreement.
- Signed predecessor hash, strict `sequence+1`, owner `store_revision+1`, and owner epoch nondecreasing by at most one versus **the supplied independent checkpoint**.
- SHA binding to complete M002 owner snapshot and M003-shaped laboratory CAS receipt content. Receipt must explicitly have `dispatch_authorized: false` and `requires_external_witness_update: true`.
- Bounded, exact UTC-second signed validity window, not more than 60 seconds; rejects expired owner leases and malformed signatures.
- Explicit `ONLINE / TIMEOUT / PARTITIONED / UNKNOWN / STALE` modeling; every partition branch blocks or requires a full signed proof before further consideration.

The only success result is **`SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF`** with `dispatch_authorized: false`, `worker_execution_authorized: false`, `current_external_high_water_verified: false`, and `independent_owner_cas_authenticity_verified: false`. The `next_checkpoint_proposal_only` is not persisted, externally sealed, or promoted by this module.

## Intentionally unresolved (and tested as weaknesses)

1. **Checkpoint rollback:** A valid Ed25519 signature does not prove its checkpoint is the **latest** independent monotonic high-water. Replaying *both* a previously signed anchor and previously accepted checkpoint/challenge/clock can still produce a structural match. This never authorizes execution. A real remote authority must enforce **fresh challenge uniqueness and externally durable anti-rollback state**, beyond this library.
2. **Receipt authenticity:** The M003-shaped receipt is not independently signed by the actual durable CAS store. A colluding signing party + forged local receipt can produce a syntactically consistent record; `independent_owner_cas_authenticity_verified` remains false.
3. **No network service or signing authority:** Test keys are ephemeral; public keys are caller pinned but the verifier cannot prove who provisioned or rotated them. It does not check revocation or authenticated live issuer status.
4. **No trustworthy clock:** Time comes from the caller. Timestamp plausibility is not proof of independently trusted time, especially under clock rollback/partition.
5. **No cross-store transaction atomicity:** M004’s two local SQLite files cannot create an atomic distributed commit, and this verifier does not make them production-safe.
6. **No side-effect fencing:** The native worker must independently and atomically check current committed fencing epochs on **every** mutating side effect; no such worker exists in this milestone.
7. **Active-owner scope:** v0 verifies a committed ACTIVE owner snapshot only, not full release, cancellation, key-rotation or handoff semantics.

## Test evidence

Run in an ephemeral environment with public Python packages:

```bash
python -m pip install pytest==9.0.2 cryptography==46.0.4
PYTHONPATH=src python -m pytest -q tests/test_m005_anchor_contract.py tests/test_m004_witness_lab.py
```

Local isolated evaluation 2026-10-13: Python 3.13, cryptography 46.0.4, pytest 9.0.2: **110 passed, 1 skipped, 0 failed** (72 M005, 38 M004). The skipped test is M004’s existing optional direct M003 adapter smoke test; it was not loaded in the disposable local environment. The unmodified M004 module and tests match the published Git blob SHAs `49c4ac2abf0af0b7bc29e1e8f32704f64e8db172` and `51b3f78b27adafa0729ad5d038b1c1e0149eecc7`.

This proves only offline/synthetic behavior, **not** GitHub Actions, a complete Phase 2 exact-SHA acceptance or a real signed external witness. GitHub Actions issue #6 currently reports zero runs.

## Required next admission gates

1. Separately provision and audit an **external immutable monotonic authority** with authenticated fresh high-water queries, challenge issuance/consumption, signature and key-rotation policies, and anti-rollback durability across host restarts and storage rollback.
2. Verify owner CAS receipt provenance from the actual authoritative store, and make prepare/commit/reconcile safe under partitions and duplicate requests.
3. Reconcile unpublished HomePC R11–R13 with exact SHA, single-writer ownership and local source custody; do not overwrite or silently import archived components.
4. Independently verify live native-worker fencing at each side effect, writer limits (one per protected namespace), three-heavy-slot admission, abort/cancel semantics, and negative fixtures.
5. Obtain actual successful exact-commit GitHub CI (issue #6), independent security review, and explicit commissioning before any production claim.

**Invariants:** `PRODUCTION_DISPATCH=BLOCKED`; `HOMEPC_NOT_CONTACTED`; `WORK_NOT_USED`; `CODE_VAULT_QUARANTINED`; `REAL_FIDELITY_NOT_TESTED`.
