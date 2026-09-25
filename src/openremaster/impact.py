from __future__ import annotations
from dataclasses import dataclass
from .evidence import EvidenceGraph

@dataclass(frozen=True)
class ImpactPlan:
    changed_evidence: frozenset[str]
    invalidated_evidence: frozenset[str]

    @property
    def reusable_evidence(self) -> bool:
        return not self.invalidated_evidence

class ShadowImpactAnalyzer:
    """Advisory only. It never schedules, mutates, or suppresses authoritative tests."""
    def analyze(self, graph: EvidenceGraph, changed_evidence: set[str]) -> ImpactPlan:
        return ImpactPlan(
            changed_evidence=frozenset(changed_evidence),
            invalidated_evidence=frozenset(graph.invalidated_by(changed_evidence)),
        )
