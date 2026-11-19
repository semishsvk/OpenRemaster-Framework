# M012 — Two Signed Head Claims, Review-Only

Status: **SYNTHETIC REVIEW ONLY — PRODUCTION DISPATCH BLOCKED**.

This module compares two Ed25519-signed recovery receipts from distinct caller-pinned authorities and public-key material. It uses the unchanged M011 signature verifier and requires exact agreement on scope, operation, probe, challenge, request hash, prior/candidate/resulting heads, sequence, owner epoch, fencing generation, result, remote operation hash and M009 receipt hash.

A mismatch, invalid signature, expired trust view, revoked signer, identical authority or overlapping public-key material fails closed. Passing only proves that two test signatures bind matching claims. The trust snapshots are caller-supplied, the current remote head is **not independently queried**, and neither issuer independence nor remote nonce consumption is proven. All results explicitly state `independent_live_current_head_verified: false`, `global_cas_authorized: false`, and `native_worker_dispatch_authorized: false`.

No network, production key, owner-state mutation, gateway call, native job, or game corpus is used. Synthetic negative tests are not production admission. Next work requires a genuine independent current-head service, trusted key lifecycle, external atomic CAS and worker-side fencing, with a separately approved canary. Preserve historical R14 149 PASS / 1 FAIL and prior immutable checkpoints.
