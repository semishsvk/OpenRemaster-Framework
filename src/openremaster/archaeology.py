from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class BinarySource:
    source_id: str
    digest: str
    byte_size: int
    locator: str = ""

    def validate(self) -> None:
        if len(self.digest) != 64:
            raise ValueError("source digest must be sha256 hex")
        if self.byte_size < 0:
            raise ValueError("byte_size must be non-negative")

@dataclass(frozen=True)
class ByteRange:
    source_id: str
    offset: int
    length: int
    digest: str

    def validate(self, source: BinarySource) -> None:
        source.validate()
        if self.source_id != source.source_id:
            raise ValueError("range source mismatch")
        if self.offset < 0 or self.length < 0 or self.offset + self.length > source.byte_size:
            raise ValueError("range outside source")
        if len(self.digest) != 64:
            raise ValueError("range digest must be sha256 hex")

@dataclass(frozen=True)
class DecoderContract:
    decoder_id: str
    decoder_version: str
    format_id: str
    parameters_digest: str

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode()).hexdigest()

@dataclass(frozen=True)
class DecodedRecord:
    record_id: str
    source_range: ByteRange
    decoder_digest: str
    output_digest: str
    record_type: str

    def validate(self) -> None:
        if len(self.decoder_digest) != 64 or len(self.output_digest) != 64:
            raise ValueError("decoded record digests must be sha256 hex")
