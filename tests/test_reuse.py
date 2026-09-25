from openremaster.cache import CacheDecision, EvidenceCache
from openremaster.domains import Domain
from openremaster.evidence import EvidenceKey, EvidenceNode
from openremaster.impact_rules import analyze_domains
from openremaster.reuse import resolve_reuse
from openremaster.testplan import plan_tests

def test_mixed_reuse_and_rerun_plan():
    plan = plan_tests(analyze_domains({Domain.AUDIO}))
    key = EvidenceKey("p", "sha", "audio-v1", "runner", "1", "audio-events")
    cache = EvidenceCache((EvidenceNode(key, "pass"),))
    checks = resolve_reuse(
        plan, cache, "p", "sha",
        {"audio-events": "audio-v1"}, "runner", "1"
    )
    assert checks[0].decision is CacheDecision.REUSE

def test_missing_digest_never_reuses():
    plan = plan_tests(analyze_domains({Domain.AUDIO}))
    checks = resolve_reuse(plan, EvidenceCache(), "p", "sha", {}, "runner", "1")
    assert checks[0].decision is CacheDecision.RERUN
    assert checks[0].reason == "missing input digest"
