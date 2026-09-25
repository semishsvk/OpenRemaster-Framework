# Game Archaeology SDK

The SDK provides project-independent deterministic primitives for reverse engineering legacy game data.

Core objects:
- BinarySource: immutable source identity, size and locator.
- ByteRange: exact offset/length provenance inside a source binary.
- DecoderContract: decoder ID/version, format identity and parameter digest.
- DecodedRecord: binds a source byte range to the decoder contract and decoded output digest.
- ReferenceGraph: typed record-to-record references with source-field provenance.
- RangeAudit: byte coverage, overlap and uncovered-byte accounting.

These primitives deliberately contain no Cadaver-specific decoding logic. OpenCadaver may export observations into this model, while its existing RE tooling remains authoritative. The same SDK can later support other legacy formats without sharing project source trees.

This is sidecar analysis infrastructure only.
