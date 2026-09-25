from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .domains import Domain
from .impact_rules import DomainImpactPlan

class Tier(str, Enum):
    FAST = "fast"
    VERIFY = "verify"

@dataclass(frozen=True)
class TestSuite:
    id: str
    tier: Tier
    domains: frozenset[Domain]

@dataclass(frozen=True)
class TestPlan:
    suites: tuple[TestSuite, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(s.id for s in self.suites)

DEFAULT_SUITES = (
    TestSuite("asset-integrity", Tier.FAST, frozenset({Domain.ASSETS})),
    TestSuite("geometry-validation", Tier.FAST, frozenset({Domain.GEOMETRY})),
    TestSuite("movement-collision", Tier.FAST, frozenset({Domain.MOVEMENT})),
    TestSuite("transition-contracts", Tier.FAST, frozenset({Domain.TRANSITIONS})),
    TestSuite("puzzle-units", Tier.FAST, frozenset({Domain.PUZZLES})),
    TestSuite("audio-events", Tier.FAST, frozenset({Domain.AUDIO})),
    TestSuite("localization-validation", Tier.FAST, frozenset({Domain.LOCALIZATION})),
    TestSuite("save-load-contracts", Tier.FAST, frozenset({Domain.SAVE_LOAD})),
    TestSuite("runtime-integration", Tier.VERIFY, frozenset({
        Domain.GEOMETRY, Domain.MOVEMENT, Domain.TRANSITIONS,
        Domain.PUZZLES, Domain.AUDIO, Domain.SAVE_LOAD,
    })),
    TestSuite("e2e-playthrough", Tier.VERIFY, frozenset({Domain.E2E})),
)

def plan_tests(impact: DomainImpactPlan, include_verify: bool = False) -> TestPlan:
    selected = []
    for suite in DEFAULT_SUITES:
        if suite.tier is Tier.VERIFY and not include_verify:
            continue
        if suite.domains.intersection(impact.invalidated):
            selected.append(suite)
    return TestPlan(tuple(selected))
