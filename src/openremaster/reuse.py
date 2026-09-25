from __future__ import annotations
from dataclasses import dataclass
from .cache import CacheDecision, CacheRequest, EvidenceCache
from .evidence import EvidenceKey
from .testplan import TestPlan

@dataclass(frozen=True)
class PlannedCheck:
    suite_id: str
    decision: CacheDecision
    reason: str

def resolve_reuse(
    plan: TestPlan,
    cache: EvidenceCache,
    project_id: str,
    source_revision: str,
    input_digests: dict[str, str],
    tool_id: str,
    tool_version: str,
) -> tuple[PlannedCheck, ...]:
    checks = []
    for suite in plan.suites:
        digest = input_digests.get(suite.id)
        if digest is None:
            checks.append(PlannedCheck(suite.id, CacheDecision.RERUN, "missing input digest"))
            continue
        key = EvidenceKey(project_id, source_revision, digest, tool_id, tool_version, suite.id)
        result = cache.decide(CacheRequest(key))
        checks.append(PlannedCheck(suite.id, result.decision, result.reason))
    return tuple(checks)
