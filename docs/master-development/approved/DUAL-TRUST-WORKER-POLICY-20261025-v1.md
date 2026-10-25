# OpenRemaster — Dual-Trust Worker Architecture v1.0
Status: APPROVED POLICY; implementation and production commissioning NOT YET VERIFIED.
Date: 2026-10-25

## Trust classes
DEVELOPMENT: may run autonomously without continuous human supervision and without production signing identity. Must enforce per-project isolation, bounded permissions, audit records, owner admission / single-writer leases, resource governor, and no access to production signing credentials or release publication. Its outputs are UNTRUSTED_DEV artifacts.
PRODUCTION: requires verified worker identity and trust anchor, isolated clean environment, attested execution context, source commit pin, independent fidelity/security gates, immutable provenance and artifact digest, and signing via separately authorized signing service. A worker signature alone does not confer release authority.

## Mandatory release gate (fail closed)
1. Authorized release request binds project, source repository, immutable commit, build recipe, dependencies and owner approval.
2. Production worker identity, admission lease, attestation, policy version, environment isolation and freshness verify independently.
3. Clean rebuild from pinned approved source; never promote a DEV binary directly.
4. Independent validation of required tests, fidelity evidence, reproducibility where feasible, SBOM/provenance and artifact SHA-256.
5. Independent release authorization; signing keys inaccessible to DEV and preferably inaccessible directly to the production build process.
6. Signing service signs exact approved artifact digest; publisher verifies signature, provenance and release authorization before publishing.
7. Missing, expired, contradictory or unverifiable evidence => DENY/HOLD; no DEV fallback, no unsigned release, no bypass via UI/API/CLI.

## Compatibility and rollout
Existing source corpora remain read-only; isolate projects and retain single-writer, owner admission, resource governor and GAME/LIGHT behavior. Introduce shadow-only policy evaluator and negative tests first; integrate all release entrypoints before enforcement. No production trust is asserted until independent end-to-end tests and owner commissioning. Do not modify active workers or shared canonical baselines without separate admission.

## Negative acceptance tests
Reject unsigned or unknown production worker; expired or replayed attestation; changed source commit; mismatched artifact digest; missing fidelity test; DEV artifact presented as release; revoked signer; missing owner lease; conflicting writer; unavailable signer; publication bypass; policy downgrade; absent provenance. Ensure DEV can still perform authorized isolated development tasks without production credentials.
