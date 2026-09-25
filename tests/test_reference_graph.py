import pytest
from openremaster.reference_graph import Reference, ReferenceGraph

def test_reference_graph_queries_both_directions():
    g = ReferenceGraph()
    g.add_record("TYPE6:1")
    g.add_record("TYPE2:86")
    g.add_reference(Reference("TYPE6:1","TYPE2:86","references","word10"))
    assert g.outgoing("TYPE6:1")[0].target_record == "TYPE2:86"
    assert g.incoming("TYPE2:86")[0].source_record == "TYPE6:1"

def test_missing_endpoint_rejected():
    g = ReferenceGraph()
    g.add_record("a")
    with pytest.raises(ValueError, match="endpoint"):
        g.add_reference(Reference("a","missing","references"))
