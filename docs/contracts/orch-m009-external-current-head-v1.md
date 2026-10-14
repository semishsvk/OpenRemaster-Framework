# M009 External Current-Head Contract v1

Status: SYNTHETIC CONTRACT ONLY / PRODUCTION_DISPATCH=BLOCKED / NO MERGE.

Parent: M008 draft PR #17, exact commit d357f5084a0b0d5acf217a76a9f15809ea0e43f0.
M007 parent: d555dd5135360e1b85e5273d4b7b5c8da7b034f3.

## Contract and implementation

The receipt is a domain-separated Ed25519 signed claim of an atomic
CAS_HEAD_AND_CONSUME_CHALLENGE operation. It binds authority, registry,
project/edition/work scope, M008 signed-envelope SHA256, previous head,
sequence, owner epoch, fence, revocation generation and unique challenge.
Canonical signed bytes follow existing M005 sorted compact JSON, not JCS.

The verifier reruns unchanged M008 (and therefore actual M005 verification)
at the identical clock. Receipt time must be current, last at most 30 seconds,
start after M008 issuance and end no later than M008 expiry.
Unknown/revoked signer, expired caller trust, wrong revocation generation,
scope mismatch, decreasing fence/epoch or prior-head mismatch reject.
Sequence advances exactly one; epoch remains equal or advances one.
Runtime counters share the wire maximum 9223372036854775000. Malformed
consumed-challenge checkpoints reject before any state change.
On the first successful commit the local checkpoint pins a SHA256 of authority,
generation, all public keys and all revoked key IDs. A different trust content
at the same generation rejects; key rotation requires a generation advance.
Trust expiry is checked on every call and excluded from this content digest so
that renewing an unchanged view does not imply a key-set change. This is local
consistency only: caller trust remains unauthenticated external evidence.
The local checkpoint also retains cumulative revocation tombstones and all
previously pinned key-ID/public-key bindings. A higher generation cannot remove
a tombstone or reuse an existing key ID for different material. Rotation uses a
new key ID; retired key bindings remain pinned even after removal from the
current view. These histories are process-local and disappear on unsafe reset;
they do not establish durable external key lifecycle or rollback resistance.

SyntheticCheckpoint provides one-process locking for head update and challenge
consumption together. Failed validation leaves it unchanged. Replayed and
concurrent identical receipts yield at most one successful acceptance.
Two differently signed candidates racing from the same prior head also yield
one winner. Partition tests preserve the unspent challenge, accept it at most
once after recovery, and reject retries when a refreshed caller trust view
revokes the signer. This tests the local model, not a deployed authority.
A false, absent or timed-out synthetic transport condition rejects before
using any cached head. No network adapter is implemented.
The caller must explicitly provide authority_outcome=COMMIT_CONFIRMED.
Unknown, timed-out or rejected outcomes fail before challenge consumption.
An acceptance followed by a lost response cannot be guessed or recommitted;
external recovery must query the same operation identity, which is still not
implemented here. Delayed receipts reject at the exact expiry boundary.
Receipt, M008 evidence and key mappings are privately copied at entry to bind
validation and local commit to the same caller evidence. Callers must not mutate
inputs during copy construction; this is not a remotely authenticated snapshot.

## Required external service semantics (NOT implemented or commissioned)

- Linearizable, durable per-scope head CAS and global single-use challenge
  consumption in ONE transaction; challenges must be unpredictable, bound to
  authenticated caller/scope/candidate and have server-enforced expiry.
- Monotonic rollback-resistant persisted sequence, owner epoch, fence and
  revocation generation, surviving crash/restart/backup restore.
- Authenticated live challenge/commit/read responses from an independently
  maintained service. A signed historical receipt alone is insufficient.
- Authenticated fresh revocation lifecycle, signer rotation and trusted time.
  Revocation must be checked atomically with commit; stale key sets must fail.
- Fail closed on partition, timeout, ambiguous commit outcome and stale quorum.
  Recovery queries the same operation identity; never guesses success or
  reuses a challenge with a different candidate.
- Cross-client/fork/race tests, crash injection and partition recovery against
  that deployed service before claiming independent current-head proof.

## Explicit limitations

TrustSnapshot, authority_available and authority_outcome are caller inputs, NOT externally current
proof. The checkpoint is mutable process-local synthetic state, not durable
storage. A restart/rollback can replay a receipt: a test preserves this limitation.
No claim of global replay prevention, external revocation freshness or current
ownership is made. All positive returns keep external_current_head_independently_verified,
durable_global_challenge_consumption_verified, current_external_revocation_verified,
rollback_resistance_verified, dispatch_authorized and worker_execution_authorized FALSE.

No production signer, network service, worker invocation, queue writer, owner
register/gateway mutation or game corpus access exists in M009. Private R14
software and test keys are not uploaded.

## Preserved evidence and production blockers

HomePC M008 checkpoint SHA256:
2036b9dcd03b6a689427224d4cc021a4079bfc0a4722eb1cb663113eac2e6f8f.
Checkpoint records M001-M008 450 PASS and separate copied R14 integration
10 PASS. Those are prior evidence, not new GitHub Actions or active R14 checks.
Frozen R14 historical suite stays 149 PASS / 1 FAIL.
Frozen pilot SHA256:
9ae886ee3c9357f720dcaebb730c99a8a7fc329a7779c8f42bb783990e54c865.

Production remains blocked by deployed external current-head authority,
authenticated independent source capture and R14 HMAC/CAS provenance,
trusted R14 string-to-numeric epoch mapping, owner-scope resolver,
gateway anti-downgrade/ACK, native worker fencing at every side effect,
exact-SHA CI and separate owner commissioning and runtime/game fidelity gates.
Do not merge into main or activate dispatch.

