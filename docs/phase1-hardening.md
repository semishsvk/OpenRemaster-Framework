# Phase 1 hardening

Phase 1 now enforces cross-component identity invariants in addition to each component's local validation.

Golden inventory, replay evidence and visual contracts must agree on project and source revision. Golden evidence links must target a known room/state and, when supplied, must match the actual evidence digests.

A framework-level integration test exercises the path from changed-file classification through domain invalidation, validation policy, minimal FAST planning, evidence reuse/rerun decisions and asset-level downstream impact.

The hardening layer is intentionally fail-closed: revision drift, unknown room/state links and digest mismatches are reported as invalid rather than silently accepted.

This still does not replace OpenAzrael/OpenCadaver project gates. Phase 1 remains a sidecar/shadow system.
