# Phase 1 acceptance checklist

Phase 1 is feature-frozen. Acceptance is based on hardening and sidecar safety, not additional scope.

## Required invariants
- deterministic identities are SHA/digest bound;
- serialized evidence rejects unsupported schemas and identity tampering;
- evidence dependency references resolve inside a complete graph;
- cross-component project/source revisions agree;
- golden links target known room/state identities;
- replay traces bind to the exact replay contract;
- visual artifacts bind to the exact capture contract;
- asset provenance rejects missing endpoints;
- cache reuse requires exact immutable identity and passing evidence.

## Sidecar boundary
- no OpenAzrael/OpenCadaver mutation API;
- no automatic commits, pushes, branch changes or source-tree generation;
- project adapters are read-only;
- FAST/VERIFY planning is advisory;
- Candidate/release gates remain project-owned.

## Acceptance execution
The repository contains automated tests for the above contracts, but Phase 1 must not be declared merge-ready solely from test source inspection. A real test execution/CI result is required before final acceptance.
