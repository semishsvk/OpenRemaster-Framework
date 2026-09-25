import pytest
from openremaster.evidence import EvidenceDependency, EvidenceGraph, EvidenceKey, EvidenceNode

def key(name: str):
    return EvidenceKey("p", "sha", "inputs", "tool", "1", name)

def test_round_trip_is_deterministic():
    graph = EvidenceGraph()
    root = graph.add(EvidenceNode(key("root"), "pass"))
    graph.add(EvidenceNode(key("child"), "pass", (EvidenceDependency(root, "input"),)))
    encoded = graph.to_json()
    restored = EvidenceGraph.from_json(encoded)
    assert restored.to_json() == encoded

def test_tampered_id_is_rejected():
    graph = EvidenceGraph([EvidenceNode(key("root"), "pass")])
    payload = graph.to_json().replace(key("root").stable_id(), "0" * 64)
    with pytest.raises(ValueError, match="evidence id mismatch"):
        EvidenceGraph.from_json(payload)

def test_dependency_type_validation():
    with pytest.raises(ValueError, match="dependency type"):
        EvidenceGraph([EvidenceNode(key("x"), "pass", (EvidenceDependency("id", "magic"),))])
