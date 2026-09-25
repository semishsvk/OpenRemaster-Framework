# Asset Provenance Graph

The asset provenance graph records how original game material becomes a runtime resource and where that resource is used.

Typical lineage:

source binary -> decoded asset -> transformed asset -> runtime resource -> room/entity

Every node has a SHA-256 content digest. Transformation edges may bind the tool ID and tool version responsible for producing the next stage.

The graph supports both directions:
- ancestors: explain exactly where a runtime entity came from,
- descendants: determine what must be reconsidered when a source or intermediate asset changes.

This enables asset-level invalidation without treating every asset change as a whole-project invalidation.

The framework remains source-safe: locators describe external/project resources but the provenance graph itself performs no writes to OpenAzrael or OpenCadaver.
