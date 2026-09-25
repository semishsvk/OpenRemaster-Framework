from hashlib import sha256
from openremaster.asset_impact import analyze_asset_impact
from openremaster.asset_provenance import AssetEdge, AssetNode, AssetProvenanceGraph
from openremaster.cache import CacheDecision, EvidenceCache
from openremaster.change_classifier import classify_paths
from openremaster.domains import Domain
from openremaster.evidence import EvidenceKey, EvidenceNode
from openremaster.impact_rules import analyze_domains
from openremaster.policy import choose_validation_policy
from openremaster.reuse import resolve_reuse
from openremaster.testplan import plan_tests

def d(v): return sha256(v.encode()).hexdigest()

def test_change_to_plan_to_cache_to_asset_impact():
    changed = set(classify_paths(("rooms/room_1/collision.gd",)))
    assert Domain.GEOMETRY in changed
    impact = analyze_domains(changed)
    policy = choose_validation_policy(impact)
    assert policy.verify_recommended
    plan = plan_tests(impact)
    assert "geometry-validation" in plan.ids

    digests = {suite.id: d(suite.id) for suite in plan.suites}
    first = plan.suites[0]
    key = EvidenceKey("openazrael","sha",digests[first.id],"runner","1",first.id)
    cache = EvidenceCache((EvidenceNode(key,"pass"),))
    checks = resolve_reuse(plan,cache,"openazrael","sha",digests,"runner","1")
    assert checks[0].decision is CacheDecision.REUSE
    assert any(c.decision is CacheDecision.RERUN for c in checks[1:])

    graph = AssetProvenanceGraph()
    graph.add_node(AssetNode("source","source",d("source")))
    graph.add_node(AssetNode("runtime","runtime",d("runtime")))
    graph.add_node(AssetNode("entity","entity",d("entity")))
    graph.add_edge(AssetEdge("source","runtime","built-from","importer","1"))
    graph.add_edge(AssetEdge("runtime","entity","used-by"))
    assert analyze_asset_impact(graph,{"source"}).affected == ("entity","runtime","source")
