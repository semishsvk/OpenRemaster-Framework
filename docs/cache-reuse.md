# Deterministic cache and evidence reuse

Evidence reuse is allowed only for an exact immutable identity match:

- project ID
- source revision / commit SHA
- input digest
- tool ID
- tool version
- check / test-suite ID

A cached failure or unknown result cannot satisfy a request that requires passing evidence.

Any revision, input, tool-version, or check-identity change produces a cache miss and therefore a rerun recommendation.

The cache does not infer equivalence from timestamps, filenames, branch names, or "latest" aliases. This keeps reuse conservative and reproducible.

During Phase 1, reuse decisions are advisory/shadow-only and cannot suppress authoritative project validation.
