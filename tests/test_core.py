import pytest
from openremaster.adapters.openazrael import OpenAzraelAdapter
from openremaster.adapters.opencadaver import OpenCadaverAdapter
from openremaster.evidence import EvidenceGraph, EvidenceKey, EvidenceNode
from openremaster.manifest import ProjectManifest

def key(check: str) -> EvidenceKey:
    return EvidenceKey("p", "sha", "inputs", "tool", "1", check)

def test_manifest_validation():
    ProjectManifest("1", "openazrael", "OpenAzrael", "openazrael").validate()

def test_manifest_rejects_bad_schema():
    with pytest.raises(ValueError):
        ProjectManifest("2", "x", "X", "x").validate()

def test_evidence_id_deterministic():
    assert key("x").stable_id() == key("x").stable_id()

def test_transitive_invalidation():
    graph = EvidenceGraph()
    a = graph.add(EvidenceNode(key("a"), "pass"))
    b = graph.add(EvidenceNode(key("b"), "pass", (a,)))
    c = graph.add(EvidenceNode(key("c"), "pass", (b,)))
    assert graph.invalidated_by({a}) == {a, b, c}

def test_read_only_adapters():
    assert OpenAzraelAdapter("a").snapshot().metadata["mode"] == "read-only"
    assert OpenCadaverAdapter("c").snapshot().metadata["mode"] == "read-only"
