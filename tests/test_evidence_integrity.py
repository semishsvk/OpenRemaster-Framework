import pytest
from openremaster.evidence import EvidenceDependency, EvidenceGraph, EvidenceKey, EvidenceNode

def key(check):
    return EvidenceKey("p","sha","inputs","tool","1",check)

def test_missing_dependency_is_rejected_by_graph_validation():
    graph = EvidenceGraph()
    graph.add(EvidenceNode(key("child"),"pass",(EvidenceDependency("missing"),)))
    with pytest.raises(ValueError, match="missing evidence dependency"):
        graph.validate_references()

def test_forward_reference_is_valid_after_graph_is_complete():
    parent = EvidenceNode(key("parent"),"pass")
    parent_id = parent.key.stable_id()
    graph = EvidenceGraph()
    graph.add(EvidenceNode(key("child"),"pass",(EvidenceDependency(parent_id),)))
    graph.add(parent)
    graph.validate_references()
