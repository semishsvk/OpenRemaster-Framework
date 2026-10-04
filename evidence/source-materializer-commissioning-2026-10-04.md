# SourceMaterializer commissioning — 2026-10-04

Canary: OpenCybermage / CYB-K002
Worker: HomePC

Worker-side reference implementation was commissioned in the isolated CYB-K002 workspace.

Observed tests:

1. Wrong expected SHA-256
   - input bytes: ASCII `abc`
   - actual SHA-256: `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`
   - supplied expected digest: all zeroes
   - result: FAIL
   - quarantine file deleted: PASS
   - attestation not created: PASS

2. Correct expected SHA-256 and size
   - expected size: 3
   - result: PASS
   - published CAS identity: `sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad`
   - SourceAttestation.v1 created: PASS
   - read_only flag: true

3. Idempotent second materialization
   - identical bytes and digest
   - existing CAS object timestamp unchanged: PASS
   - second quarantine file removed: PASS
   - no divergent CAS object required: PASS

4. Secret hygiene
   - second attestation scanned for `http://`, `https://`, `token`, `cookie`, and `sig=`
   - secret-bearing match: false

Remaining capability boundary:
The trusted broker that streams an opaque connector `file_uri` directly into the worker quarantine path is not exposed by the currently connected tool surface. Model-mediated forwarding of credential-bearing presigned URLs is explicitly prohibited by SourceMaterializer.v1.

Therefore worker publication semantics are STRUCTURAL/commissioned; connector-to-worker broker transport remains BLOCKED pending a first-class trusted transfer capability.
