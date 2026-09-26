from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .freshness import EvidenceFreshness, Freshness
from .identity import EvidenceIdentity


class EvidenceStage(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    VALIDATED = "validated"
    HYPOTHESIS = "hypothesis"
    REJECTED = "rejected"


_ALLOWED_TRANSITIONS = {
    EvidenceStage.OBSERVED: frozenset({EvidenceStage.DERIVED, EvidenceStage.VALIDATED, EvidenceStage.HYPOTHESIS, EvidenceStage.REJECTED}),
    EvidenceStage.DERIVED: frozenset({EvidenceStage.VALIDATED, EvidenceStage.HYPOTHESIS, EvidenceStage.REJECTED}),
    EvidenceStage.HYPOTHESIS: frozenset({EvidenceStage.DERIVED, EvidenceStage.VALIDATED, EvidenceStage.REJECTED}),
    EvidenceStage.VALIDATED: frozenset(),
    EvidenceStage.REJECTED: frozenset(),
}


@dataclass(frozen=True)
class LifecycleEvidence:
    identity: EvidenceIdentity
    stage: EvidenceStage
    evidence_id: str
    reason: str = ""

    def validate(self) -> None:
        self.identity.validate()
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if self.stage is EvidenceStage.REJECTED and not self.reason.strip():
            raise ValueError("rejected evidence requires reason")

    def transition(self, target: EvidenceStage, reason: str = "") -> "LifecycleEvidence":
        self.validate()
        if target == self.stage:
            return self
        if target not in _ALLOWED_TRANSITIONS[self.stage]:
            raise ValueError(f"invalid evidence lifecycle transition: {self.stage.value}->{target.value}")
        candidate = LifecycleEvidence(self.identity, target, self.evidence_id, reason)
        candidate.validate()
        return candidate

    def require_usable(self, freshness: EvidenceFreshness) -> None:
        self.validate()
        freshness.validate()
        if freshness.evidence_id != self.evidence_id:
            raise ValueError("freshness evidence identity mismatch")
        if freshness.freshness is Freshness.STALE:
            raise ValueError("stale evidence is not usable")
        if self.stage is not EvidenceStage.VALIDATED:
            raise ValueError(f"evidence stage is not validated: {self.stage.value}")
