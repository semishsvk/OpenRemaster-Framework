# Provenance and invalidation reports

Every advisory REUSE/RERUN decision can be rendered as deterministic provenance.

A provenance record binds:
- test-suite ID,
- decision and reason,
- project ID,
- exact source revision,
- exact input digest,
- tool ID/version,
- derived immutable evidence ID.

Invalidation reports combine the direct change domains, transitive invalidation set, validation policy and per-check provenance.

The local JSON evidence store is content-addressed by evidence identity and verifies identity again on read. It is intended for framework-owned cache/artifact directories, never project source trees.
