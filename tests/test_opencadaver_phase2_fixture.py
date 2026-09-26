import pytest

from openremaster.freshness import Freshness, ProvenanceFreshness
from openremaster.opencadaver_fixture import build_opencadaver_verified_fixture


def by_id(items):
    return {item.evidence_id: item for item in items}


def test_verified_opencadaver_chain_is_current_and_usable():
    fixture = build_opencadaver_verified_fixture()
    freshness = by_id(ProvenanceFreshness(fixture.graph).evaluate(set()))
    assert all(item.freshness is Freshness.CURRENT for item in freshness.values())
    for item in fixture.lifecycle:
        item.require_usable(freshness[item.evidence_id])


def test_k133_source_change_stales_k134_and_k137_transitively():
    fixture = build_opencadaver_verified_fixture()
    freshness = by_id(fixture.freshness_after_source_change())
    assert freshness[fixture.source_id].freshness is Freshness.STALE
    assert freshness[fixture.framing_id].freshness is Freshness.STALE
    assert freshness[fixture.support_id].freshness is Freshness.STALE
    assert freshness[fixture.support_id].stale_roots == (fixture.source_id,)


def test_stale_k137_is_rejected_even_though_historical_status_is_pass_and_lifecycle_validated():
    fixture = build_opencadaver_verified_fixture()
    freshness = by_id(fixture.freshness_after_source_change())
    k137 = next(item for item in fixture.lifecycle if item.evidence_id == fixture.support_id)
    assert fixture.graph.get(fixture.support_id).status == "pass"
    with pytest.raises(ValueError, match="stale"):
        k137.require_usable(freshness[fixture.support_id])


def test_fixture_is_deterministic():
    first = build_opencadaver_verified_fixture()
    second = build_opencadaver_verified_fixture()
    assert first.graph.to_json() == second.graph.to_json()
    assert tuple(item.identity.digest() for item in first.lifecycle) == tuple(
        item.identity.digest() for item in second.lifecycle
    )
