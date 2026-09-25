from __future__ import annotations
from dataclasses import dataclass
from .bundle import ReplayEvidenceBundle

@dataclass(frozen=True)
class ReproductionResult:
    reproducible: bool
    reason: str

def verify_reproduction(expected_bundle_digest: str, observed: ReplayEvidenceBundle) -> ReproductionResult:
    actual = observed.digest()
    if actual == expected_bundle_digest:
        return ReproductionResult(True, "exact replay evidence bundle match")
    return ReproductionResult(False, f"bundle mismatch: expected {expected_bundle_digest}, observed {actual}")
