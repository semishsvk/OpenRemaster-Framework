# Golden Master Explorer model

The Golden Master model is a source-revision-bound inventory of rooms and their meaningful states.

Coverage is measured per room/state rather than only per room. This matters for multi-state locations such as the OpenAzrael Ziggurat: each meaningful state is an independent coverage target.

A room/state can link three independent evidence classes:
- deterministic replay bundle,
- visual baseline,
- asset provenance graph.

Coverage reports are evidence-kind-specific. A project can therefore have complete visual coverage while still missing replay coverage, or vice versa.

Phase 1 defines only the deterministic inventory, links and coverage calculations. It does not scrape or mutate OpenAzrael/OpenCadaver and does not declare project release readiness.
