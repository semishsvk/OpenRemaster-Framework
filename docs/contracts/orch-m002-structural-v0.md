# ORCH-M002 — Structural safety contracts v0

Status: DRAFT / CONTRACT_RESEARCH_ONLY. No production authorization, dispatch, transport, HomePC, original game data, worker execution, credentials, or database mutations.

## Authority model

This is a standalone, pure Python synthetic safety model stacked on M001 (commit ec415f36e86a74cf7e3d651569a437eea0a25585). It is NOT a replacement for any newer unpublished HomePC K003/K004/R11–R13 code.

- Owner acquire, renew, release: return only *proposals* with expected durable store revision, incrementing owner epoch on acquire, and requires_atomic_durable_cas=true. They never acquire a lease or authorize a side effect.
- Fence matching: exact owner, job, attempt, epoch, active expiry. Returns only STRUCTURAL_MATCH_NOT_AUTHORIZED. Epoch rollback, persisted CAS, signatures, clock authority and worker-side fencing are outside this module.
- Event journal: strict sequence, SHA-256 hash chain, job identity and per-attempt state transitions. Newer unknown execution remains BLOCKED even if an older attempt completed. A hash chain is NOT authenticated provenance.
- Receipt: binds job/attempt/worker/owner epoch/source SHA/corpus SHA to actual evidence bytes. Even a consistent PASS field yields only BOUND_UNAUTHENTICATED_NOT_ACCEPTED, not verified semantics or authorization.
- Fail closed on invalid timestamps, schemas, bool-as-int, extra/missing fields, stale attempts or owners, expired leases, malformed or reordered events, changed receipt/evidence and nonadvancing serialized renewals.

Do not infer that concurrent acquisition is safe from a pure proposal. Two contenders could propose against the same snapshot; an external, authoritative atomic durable CAS must choose exactly one, and every side-effecting worker must enforce the committed epoch.

## Testing

Run only isolated, non-network synthetic tests:

    PYTHONPATH=src python -m pytest -q tests/test_m002_structural.py

Snapshot acceptance: 41 isolated tests PASS on Python 3.13 (local disposable sandbox). This is NOT GitHub Actions PASS or complete Framework Phase 2 acceptance. The GitHub Actions zero-run blocker is issue #6.

## Required before M002 production admission

1. Reconcile any HomePC code with immutable SHA and version ownership; do not overwrite R11–R13.
2. Durable, transactional CAS and monotonic fencing authority, independent signatures/authentication, revocation and anti-replay (including store rollback).
3. Signed and independently verified capacity/worker attestations, max-three-heavy-slot writer policy, and worker-enforced epoch checks for every side effect.
4. Authenticated, complete, per-job/attempt journal and trustworthy time source.
5. Verified evidence bytes *and meaning*, signed receipt, provenance/authorization, and exact SHA-bound failure-injection tests.
6. Actual GitHub CI run before remote validation accepted; independent live commissioning before runtime or fidelity claims.

Until these gates pass, keep production dispatch BLOCKED and recovered source in quarantine. Relevant tracking: issues #5 and #6.
