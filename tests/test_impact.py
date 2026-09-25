from openremaster.evidence import EvidenceDependency, EvidenceGraph, EvidenceKey, EvidenceNode
from openremaster.impact import ShadowImpactAnalyzer

def key(name: str):
    return EvidenceKey("p", "sha", "inputs", "tool", "1", name)

def test_shadow_impact_is_transitive_and_advisory():
    graph = EvidenceGraph()
    a = graph.add(EvidenceNode(key("asset"), "pass"))
    b = graph.add(EvidenceNode(key("room"), "pass", (EvidenceDependency(a, "input"),)))
    c = graph.add(EvidenceNode(key("playthrough"), "pass", (EvidenceDependency(b, "runtime"),)))
    plan = ShadowImpactAnalyzer().analyze(graph, {a})
    assert plan.invalidated_evidence == frozenset({a, b, c})
