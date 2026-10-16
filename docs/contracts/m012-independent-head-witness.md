# ORCH-M012 — Independent Head Witness Review Contract v1

**Status: OFFLINE TWO-SIGNATURE CROSS-CHECK PASS / EXTERNAL CURRENTNESS NOT AUTHENTICATED / PRODUCTION DISPATCH BLOCKED.**

## Scope

M012 consumes an unchanged M011 signed remote-recovery receipt and a separately signed, domain-separated Ed25519 witness about the same operation, challenge and resulting head. Both trust snapshots and signatures are **caller-supplied laboratory evidence**. The code does not contact an independent remote service, does not consume a global nonce, and does not grant owner or worker execution authority.

Parent: M011 draft PR #21, exact SHA `c29598e668e5d34132965528eadef13a399889e4`; HomePC frozen checkpoint SHA256 `cbec7f374676d62e58bd4ac75fae56daa5a129db5a9215a65b09ce58ceb7729a`. All 41 inherited Git source objects are copied byte-for-byte to a separate workspace. The R14 historical 149 PASS / 1 FAIL remains untouched.

## Signed witness contract

- Exact schema `ORF-M012.IndependentHeadWitness.v1`, audience `ORF-IndependentCurrentHead-ReviewOnly-v1` and Ed25519 signing context `OpenRemaster|M012-IndependentHeadWitness|v1\0`.
- Separate witness authority and public-key namespace; reject the same receipt and witness authority. Caller-pinned public keys, key IDs, revocations, generation and expiry must be explicit and well-formed.
- Bind witness signature to the exact SHA256 of the validated M011 receipt, authority, project scope, operation ID, probe ID, exact challenge, resulting remote head, sequence, epoch and fence, issued/expiry UTC seconds.
- Revalidate M011's actual Ed25519 signature using the unchanged M011 verifier; reject malformed, stale, future, revoked, unknown-key, wrong-authority, inconsistent or replay-looking claims.
- For signed COMMITTED, the witness must match the claimed candidate head and M011 sequence/epoch/fence. For signed REJECTED, it matches the prior head and a synthetic predecessor sequence/epoch/fence assumption. **This assumption is NOT a real canonical owner-epoch mapping and must be replaced with an independently sourced predecessor record before deployment.**
- The result reports only `TWO_SIGNATURES_CROSS_BOUND_REVIEW_ONLY`, signed bytes verified, and `externally_current_highwater_verified=false`, `witness_currentness_authenticated_from_live_service=false`, `global_nonce_consumption_verified=false`, `remote_cas_receipt_independently_verified=false`, `owner_scope_epoch_mapping_verified=false`, `native_worker_side_effect_fencing_verified=false`, `dispatch_authorized=false`, `worker_execution_authorized=false`.

## Explicit security limits

Two signatures are not two independent *live* authorities. A caller may supply two old but valid signed documents, stale trust views, or test-only signer keys. This module cannot prove the witness is the latest high-water, the nonce was globally consumed, the signed remote result is genuine native execution, or a new owner cannot supersede the old one after signature issuance. There is no durable current-head lookup, no trusted remote revocation service, no external CAS, no worker-side fence, no live owner-scope authority and no native receiver ACK.

All positive tests are review-only. Do not expose this result as a production authorization flag, mutate the active HomePC owner registry, launch K003/native jobs, or merge to main on the basis of synthetic PASS.

## HomePC isolated tests

New Python module `src/openremaster/m012_independent_head_witness.py`, tests `tests/test_m012_independent_head_witness.py`, this contract, and read-only workflow. All new files live on an isolated M012 worktree. The selected M001–M012 regression suite must pass and have its exact Git blob IDs and test logs recorded before review acceptance.

## Production gates

1. Authenticated independent live current-head service with durable monotonic sequence and actual remote signed response at request time.
2. Globally consumed nonce/challenge, external CAS and durable receipt/ACK correlation across process crashes.
3. Separately trusted canonical owner scope, R14 string epoch ↔ numeric epoch mapping and real predecessor state for REJECTED outcomes.
4. Signer rotation/revocation currentness, partition-safe recovery, native receiver fencing at each side effect.
5. Explicit owner-approved canary and game-specific fidelity validation; maintain single-writer and three-heavy-slot policy.

**PRODUCTION_DISPATCH=BLOCKED.**
