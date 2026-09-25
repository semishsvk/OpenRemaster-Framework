from __future__ import annotations
from dataclasses import dataclass
from .visual import VisualArtifact

@dataclass(frozen=True)
class VisualComparison:
    exact_match: bool
    comparable: bool
    reason: str

def compare_visual_artifacts(expected: VisualArtifact, observed: VisualArtifact) -> VisualComparison:
    expected.validate()
    observed.validate()
    if expected.contract_digest != observed.contract_digest:
        return VisualComparison(False, False, "capture contracts differ")
    if expected.image_digest == observed.image_digest:
        return VisualComparison(True, True, "exact image digest match")
    return VisualComparison(False, True, "same capture contract, image digest differs")
