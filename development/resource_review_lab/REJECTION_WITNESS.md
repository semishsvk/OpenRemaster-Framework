# Explicit rejection snapshot mapping through existing M011/M012

The audit snapshot is not a recovery head. This crosswalk hashes a domain-separated mapping that includes the exact audit byte digest/count, immutable source revision, recovery scope/operation/probe/challenge, authority IDs, trust generations and sequence floor. The existing signed M011 request_sha256 must equal that mapping digest. Existing M012 then verifies the exact receipt and a separate witness signature with its unchanged freshness and full key-domain separation checks. Existing rejection import verifies the snapshot bytes.

No signature schema, signing implementation, authority, witness service or key is introduced. Tests use ephemeral synthetic fixture keys only. Both existing M011/M012 source hashes are pinned. The recovery head retains its original meaning and is deliberately different from the audit byte digest in tests.

Valid signatures prove the mapping was signed under caller-supplied trust views. They do not prove live witness currentness, independent trust enrollment, actual source revision content, durable complete audit storage or release eligibility. Every result is HOLD with dispatch/sign/publish/promote/fallback disabled. Expected context and trust views require a future independently verified authority; no live connection or activation is performed.
