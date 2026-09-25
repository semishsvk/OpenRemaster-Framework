from openremaster.baseline import register_source_baseline
from openremaster.evidence import EvidenceGraph
from openremaster.snapshot import SourceSnapshot

def test_baseline_is_sha_bound():
    graph = EvidenceGraph()
    snapshot = SourceSnapshot("p", "owner/p", "deadbeef", "manifest")
    result = register_source_baseline(graph, snapshot, "0.1.0")
    node = graph.get(result.evidence_id)
    assert node.key.source_revision == "deadbeef"
    assert node.key.input_digest == "manifest"
