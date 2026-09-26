from __future__ import annotations
from dataclasses import dataclass
from .domains import Domain
from .impact_rules import DomainImpactPlan

INTEGRATION_DOMAINS = frozenset({
    Domain.GEOMETRY, Domain.MOVEMENT, Domain.TRANSITIONS,
    Domain.PUZZLES, Domain.SAVE_LOAD, Domain.E2E,
})

@dataclass(frozen=True)
class ValidationPolicy:
    fast_required: bool
    verify_recommended: bool
    reason: str

def choose_validation_policy(impact: DomainImpactPlan) -> ValidationPolicy:
    if not impact.invalidated:
        return ValidationPolicy(False, False, "no impacted domains")
    integration = impact.invalidated.intersection(INTEGRATION_DOMAINS)
    # E2E is a downstream aggregate for isolated audio/localization too.
    # An explicit E2E change still warrants VERIFY.
    if Domain.E2E not in impact.changed:
        integration = integration - {Domain.E2E}
    if integration:
        names = ",".join(sorted(d.value for d in integration))
        return ValidationPolicy(True, True, f"integration impact: {names}")
    return ValidationPolicy(True, False, "isolated domain impact")
