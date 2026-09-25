from __future__ import annotations
from dataclasses import dataclass
from .domains import DEFAULT_DEPENDENCIES, Domain

@dataclass(frozen=True)
class DomainImpactPlan:
    changed: frozenset[Domain]
    invalidated: frozenset[Domain]

def analyze_domains(changed: set[Domain]) -> DomainImpactPlan:
    invalidated = set(changed)
    progress = True
    while progress:
        progress = False
        for domain, dependencies in DEFAULT_DEPENDENCIES.items():
            if domain not in invalidated and dependencies.intersection(invalidated):
                invalidated.add(domain)
                progress = True
    return DomainImpactPlan(frozenset(changed), frozenset(invalidated))
