from openremaster.cache import CacheDecision, CacheRequest, EvidenceCache
from openremaster.evidence import EvidenceKey, EvidenceNode

def key(revision="sha", digest="inputs", version="1"):
    return EvidenceKey("p", revision, digest, "tool", version, "check")

def test_exact_pass_is_reused():
    cache = EvidenceCache((EvidenceNode(key(), "pass"),))
    assert cache.decide(CacheRequest(key())).decision is CacheDecision.REUSE

def test_revision_change_forces_rerun():
    cache = EvidenceCache((EvidenceNode(key(), "pass"),))
    assert cache.decide(CacheRequest(key(revision="new"))).decision is CacheDecision.RERUN

def test_input_change_forces_rerun():
    cache = EvidenceCache((EvidenceNode(key(), "pass"),))
    assert cache.decide(CacheRequest(key(digest="changed"))).decision is CacheDecision.RERUN

def test_tool_version_change_forces_rerun():
    cache = EvidenceCache((EvidenceNode(key(), "pass"),))
    assert cache.decide(CacheRequest(key(version="2"))).decision is CacheDecision.RERUN

def test_failed_evidence_is_not_reused_as_pass():
    cache = EvidenceCache((EvidenceNode(key(), "fail"),))
    assert cache.decide(CacheRequest(key())).decision is CacheDecision.RERUN
