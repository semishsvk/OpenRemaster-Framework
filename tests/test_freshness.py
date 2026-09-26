import pytest

from openremaster.evidence import EvidenceDependency, EvidenceGraph, EvidenceKey, EvidenceNode
from openremaster.freshness import Freshness, ProvenanceFreshness


def key(name: str) -> EvidenceKey:
    return EvidenceKey("p", "sha", "inputs", "tool", "1", name)


def graph():
    g = EvidenceGraph()
    root_a = g.add(EvidenceNode(key("root-a"), "pass"))
    root_b = g.add(EvidenceNode(key("root-b"), "pass"))
    mid = g.add(EvidenceNode(key("mid"), "pass", (EvidenceDependency(root_a, "input"),)))
    leaf = g.add(EvidenceNode(
        key("leaf"), "pass",
        (EvidenceDependency(mid, "derived"), EvidenceDependency(root_b, "input")),
    ))
    independent = g.add(EvidenceNode(key("independent"), "pass"))
    return g, root_a, root_b, mid, leaf, independent


def as_map(result):
    return {item.evidence_id: item for item in result}


def test_stale_propagates_transitively_without_mutating_evidence_status():
    g, root_a, _, mid, leaf, independent = graph()
    before = g.to_json()
    result = as_map(ProvenanceFreshness(g).evaluate({root_a}))
    assert result[root_a].freshness is Freshness.STALE
    assert result[mid].freshness is Freshness.STALE
    assert result[leaf].freshness is Freshness.STALE
    assert result[independent].freshness is Freshness.CURRENT
    assert result[leaf].stale_roots == (root_a,)
    assert g.to_json() == before
    assert g.get(leaf).status == "pass"


def test_multiple_stale_roots_are_sorted_and_deterministic():
    g, root_a, root_b, _, leaf, _ = graph()
    evaluator = ProvenanceFreshness(g)
    first = evaluator.evaluate({root_b, root_a})
    second = evaluator.evaluate({root_a, root_b})
    assert first == second
    assert as_map(first)[leaf].stale_roots == tuple(sorted((root_a, root_b)))


def test_empty_change_set_keeps_all_evidence_current():
    g, *_ = graph()
    assert all(item.freshness is Freshness.CURRENT for item in ProvenanceFreshness(g).evaluate(set()))


def test_unknown_changed_evidence_fails_closed():
    g, *_ = graph()
    with pytest.raises(ValueError, match="unknown changed evidence"):
        ProvenanceFreshness(g).evaluate({"missing"})


def test_dangling_graph_is_rejected_before_freshness_evaluation():
    g = EvidenceGraph()
    g.add(EvidenceNode(key("child"), "pass", (EvidenceDependency("missing"),)))
    with pytest.raises(ValueError, match="missing evidence dependency"):
        ProvenanceFreshness(g)


def test_freshness_value_rejects_inconsistent_state_at_boundary():
    from openremaster.freshness import EvidenceFreshness

    with pytest.raises(ValueError, match="current evidence"):
        EvidenceFreshness("e", Freshness.CURRENT, ("root",)).validate()
    with pytest.raises(ValueError, match="requires stale roots"):
        EvidenceFreshness("e", Freshness.STALE).validate()
    with pytest.raises(ValueError, match="unique and sorted"):
        EvidenceFreshness("e", Freshness.STALE, ("b", "a", "a")).validate()
