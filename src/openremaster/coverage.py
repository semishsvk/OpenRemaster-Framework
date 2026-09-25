from __future__ import annotations
from dataclasses import dataclass
from .golden import GoldenInventory

@dataclass(frozen=True)
class CoverageEvidence:
    room_id: str
    state_id: str
    kind: str
    evidence_digest: str

@dataclass(frozen=True)
class CoverageReport:
    required: int
    covered: int
    missing: tuple[tuple[str, str], ...]

    @property
    def complete(self) -> bool:
        return self.required == self.covered

def analyze_coverage(
    inventory: GoldenInventory,
    evidence: tuple[CoverageEvidence, ...],
    required_kind: str,
) -> CoverageReport:
    inventory.validate()
    required = {
        (room.room_id, state.state_id)
        for room in inventory.rooms
        for state in room.states
    }
    covered = {
        (e.room_id, e.state_id)
        for e in evidence
        if e.kind == required_kind and e.evidence_digest
    } & required
    missing = tuple(sorted(required - covered))
    return CoverageReport(len(required), len(covered), missing)
