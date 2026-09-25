from __future__ import annotations
from dataclasses import dataclass
from .archaeology import BinarySource, ByteRange

@dataclass(frozen=True)
class RangeAudit:
    covered_bytes: int
    overlap_bytes: int
    uncovered_bytes: int

def audit_ranges(source: BinarySource, ranges: tuple[ByteRange, ...]) -> RangeAudit:
    source.validate()
    coverage = [0] * source.byte_size
    for item in ranges:
        item.validate(source)
        for i in range(item.offset, item.offset + item.length):
            coverage[i] += 1
    covered = sum(1 for n in coverage if n > 0)
    overlap = sum(1 for n in coverage if n > 1)
    return RangeAudit(covered, overlap, source.byte_size - covered)
