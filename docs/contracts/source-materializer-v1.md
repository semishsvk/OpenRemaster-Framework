# SourceMaterializer / ArtifactTransfer Contract v1

Status: vNext / Orchestrator contract. Does not reopen the frozen Phase 1 baseline.

## Purpose

Materialize an authoritative connector-backed source artifact onto an authorized execution worker without routing source bytes through GitHub or exposing provider credentials to model-visible logs.

## Security boundary

A provider/connector may return an opaque file reference containing a short-lived credential-bearing download URL. That URL is a secret capability.

MUST:
- pass the opaque reference only through a trusted transfer broker;
- redact download URLs, query strings, bearer tokens and cookies from logs, FailureBundles and Evidence Ledger entries;
- bind the request to an explicit destination worker and expected artifact identity;
- download into a temporary quarantine path;
- compute SHA-256 before publication;
- compare SHA-256 to the expected immutable source digest;
- atomically publish passing bytes into worker CAS/staging;
- emit a non-secret SourceAttestation containing provider artifact ID, logical name, size, SHA-256, worker identity, timestamps and final CAS ref;
- delete quarantine bytes on failure.

MUST NOT:
- commit authoritative retail bytes to GitHub;
- put presigned URLs in repository files, job arguments, shell history, durable logs or model-visible evidence;
- promote an artifact whose expected digest is absent or mismatched;
- treat connector metadata alone as byte-level verification.

## Request

SourceMaterializeRequest.v1:
- source_ref: opaque connector file reference
- logical_name
- expected_sha256
- expected_size (optional but recommended)
- destination_worker
- destination_namespace
- read_only: true for authoritative game corpora
- correlation_id

## Result

SourceAttestation.v1:
- logical_name
- provider_artifact_id (non-secret)
- size
- sha256
- destination_worker
- cas_ref
- materialized_path
- read_only
- started_utc
- completed_utc
- result: PASS | FAIL

The result MUST NOT contain source_ref credentials.

## Worker algorithm

1. Resolve worker capability and allowed destination root.
2. Create a unique quarantine file under the worker execution root.
3. Broker streams bytes from source_ref directly to the worker.
4. Close stream and compute SHA-256 locally.
5. Check expected size when supplied.
6. Compare digest using exact lowercase hexadecimal equality.
7. On mismatch: delete quarantine file and return FAIL.
8. On PASS: atomically move into content-addressed storage or immutable materialized staging.
9. Mark authoritative corpus materialization read-only where the platform supports it.
10. Emit SourceAttestation.v1.

## CyberMage commissioning canary

Worker: HomePC
Workspace: F:\\OpenRemaster\\OpenCybermage\\CYB-K002
Canonical staging: input/

Required artifacts:
- CM_HI.EXE — d232d915d904953e30462a827b25e05bf933793ad5277af7c600b0305096735b
- SCENE.RSC — 8eb628c4d63ff6f32599ec1537e00f611388f1f7d6883d512c0a0e6dfaa21c68
- FXO.RSC — 1871f2aaad8b6478b9abe645c9ee3ab18f9ec0154c19c14f9af646e8d1e1a3bc
- PANEL00.DAT — e985eba05733c43250472ccadcff5f39892c470f54768fbbc05c1f4e5186c226
- ANMH.RSC — c036e638c274278bc11f3a03e4118483f704f1f25a5895df472495350eb7e933
- HIPAK.RSC — 85caf0e361ce4db5892d2432d1b5cec6a7de536d80a491784b1ca9bd1fd79bbd

Acceptance:
1. All six transfers return PASS.
2. HomePC local preflight independently recomputes all six hashes and returns PASS.
3. input_attestation.json contains no URL/token/cookie.
4. A second materialization is idempotent: identical digest resolves to the same CAS identity and does not create divergent authoritative bytes.
5. Deliberate wrong expected digest fails closed and leaves no published file.
