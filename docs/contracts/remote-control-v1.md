# Remote control plane M001 / v1

Status: draft contract and synthetic validation only. No transport or worker
execution is implemented. No game/runtime VERIFIED claim follows from CI.

## Scope and authority

M001 defines request, worker-status and receipt JSON Schema Draft 2020-12
documents under `contracts/remote-control/v1/`. Validate every document
with date-time format assertions before calling `check_binding`.
Reject unknown properties and versions. Missing worker information is UNKNOWN.
Only `synthetic.validate` is permitted. No shell commands, filesystem paths,
source credentials or game bytes are accepted by these contracts.

GitHub is a review/checkpoint surface. Canonical main, local work and original
corpora remain outside the control plane's mutation authority. This milestone
does not use HomePC or deploy a service.

## Binding and bounded work

Requests identify a destination worker, immutable 40-character Git revision,
input SHA-256, idempotency key and UTC deadline. Limits cap work at 60 seconds
and output at 1 MiB. The eventual executor MUST enforce these limits, recheck
expiry at dispatch, authenticate both endpoints and authorize the operation.

Worker status is advisory and expires after 60 seconds; future observations
are rejected. READY requires a supported capability. Readiness grants no
authorization. The receipt binds request ID, worker ID, revision and the digest
of the entire request. PASS requires an evidence digest and no error code.
A digest reference alone is not evidence verification; consumers MUST fetch
and verify evidence bytes before promoting any claim.

Canonical identity is SHA-256 of UTF-8 JSON with sorted object keys, compact
separators, Unicode preserved and non-finite numbers rejected. Arrays preserve
order. This is the Python contract encoding, not RFC 8785.

## Idempotency and lifecycle reserved for M002

A future durable dispatcher MUST bind (worker_id, idempotency_key) to request
digest: replay the saved result for an identical digest, reject a different
digest, and atomically claim execution before dispatch. Crash recovery,
cancellation, authentication, retries, evidence storage and transport remain
unimplemented. UNKNOWN never implies success; only an independently verified
receipt/evidence pair can support a validation claim.

## Compatibility and validation

Version 1.0 is strict and immutable once adopted; incompatible changes require
a new version directory and explicit adapter. Never silently coerce payloads.
Synthetic fixtures use invented identities and digests. CI validates schemas,
required fields, limits, unsupported operations, malformed timestamps,
receipt substitution, unavailable/stale workers, expiry and digest stability.
It runs on GitHub-hosted Ubuntu with read-only repository permission, no
credentials retained and a five-minute job bound. It does not replace Phase 2
clean-checkout exact-SHA acceptance or run reconstruction jobs.

Run: `python -m pip install pytest==8.3.5 jsonschema==4.23.0`, then
`python -m pytest -q tests/test_remote_control_contracts.py`.
