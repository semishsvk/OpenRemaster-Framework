from hashlib import sha256
import pytest
from openremaster.asset_impact import analyze_asset_impact
from openremaster.asset_provenance import AssetEdge, AssetNode, AssetProvenanceGraph

def digest(value):
    return sha256(value.encode()).hexdigest()

def graph():
    g = AssetProvenanceGraph()
    for node in (
        AssetNode("binary","source",digest("binary"),"legacy/game.dat"),
        AssetNode("texture","decoded",digest("texture"),"decoded/keyhole.raw"),
        AssetNode("png","transformed",digest("png"),"generated/keyhole.png"),
        AssetNode("resource","runtime",digest("resource"),"res://keyhole.png"),
        AssetNode("room-entity","entity",digest("entity"),"room-1/keyhole"),
    ):
        g.add_node(node)
    g.add_edge(AssetEdge("binary","texture","decoded-from","decoder","1"))
    g.add_edge(AssetEdge("texture","png","transformed-from","texture-lab","1"))
    g.add_edge(AssetEdge("png","resource","built-from","importer","1"))
    g.add_edge(AssetEdge("resource","room-entity","used-by"))
    return g

def test_full_lineage_is_queryable():
    g = graph()
    assert g.ancestors("room-entity") == ("binary","png","resource","texture")
    assert g.descendants("binary") == ("png","resource","room-entity","texture")

def test_source_change_propagates_to_runtime_entity():
    impact = analyze_asset_impact(graph(), {"binary"})
    assert impact.affected == ("binary","png","resource","room-entity","texture")

def test_transformed_asset_change_does_not_invalidate_source():
    impact = analyze_asset_impact(graph(), {"png"})
    assert impact.affected == ("png","resource","room-entity")

def test_graph_digest_is_deterministic():
    assert graph().digest() == graph().digest()

def test_missing_endpoint_is_rejected():
    g = AssetProvenanceGraph()
    g.add_node(AssetNode("a","source",digest("a")))
    with pytest.raises(ValueError, match="endpoint"):
        g.add_edge(AssetEdge("a","missing","decoded-from"))
