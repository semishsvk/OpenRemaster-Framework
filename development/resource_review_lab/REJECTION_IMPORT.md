# Read-only rejection snapshot import v1

The importer accepts bytes, an externally supplied expected SHA-256 of those exact bytes, and an expected record count. It rejects more than 256 KiB, missing expectations, wrong hashes, invalid UTF-8, duplicate JSON keys, nonfinite values, invalid schema, unknown fields, duplicate attempts, changed order/count and altered record/export digests. It reuses the existing rejection exporter as the schema and internal-integrity validator. No filesystem read/write, live authority or journal is added.

The expected hash is not taken from the imported bundle. Its independent origin must be established by the future caller; this module cannot prove it. Tests deliberately show that supplying a newly calculated hash for a coherently changed valid snapshot can satisfy integrity while still returning HOLD with authenticity, durability, completeness and authority unverified. Byte equality against a trusted snapshot is not proof of a complete or fresh history and never authorizes dispatch/sign/publish/promote/fallback.

Pretty-printed JSON is permitted when its exact bytes match the expectation. The internal export digest and exact-byte digest are separate. The importer does not replace or modify existing source witnesses, identity verification, owner admission or the production security gates.
