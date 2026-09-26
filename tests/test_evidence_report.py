import json
from dataclasses import replace

import pytest

from openremaster.evidence_report import EvidenceReport, build_evidence_report
from openremaster.freshness import EvidenceFreshness, Freshness, ProvenanceFreshness
from openremaster.opencadaver_fixture import build_opencadaver_verified_fixture


def test_opencadaver_report_round_trip_is_deterministic():
    fixture = build_opencadaver_verified_fixture()
    freshness = ProvenanceFreshness(fixture.graph).evaluate(set())
    report = build_evidence_report(fixture.lifecycle, freshness)
    encoded = report.canonical_json()
    restored = EvidenceReport.from_json(encoded)
    assert restored.canonical_json() == encoded
    assert restored.digest() == report.digest()


def test_stale_roots_survive_serialization():
    fixture = build_opencadaver_verified_fixture()
    report = build_evidence_report(fixture.lifecycle, fixture.freshness_after_source_change())
    restored = EvidenceReport.from_json(report.canonical_json())
    k137 = next(record for record in restored.records if record.evidence_id == fixture.support_id)
    assert k137.freshness.freshness is Freshness.STALE
    assert k137.freshness.stale_roots == (fixture.source_id,)


def test_report_rejects_lifecycle_freshness_set_mismatch():
    fixture = build_opencadaver_verified_fixture()
    freshness = ProvenanceFreshness(fixture.graph).evaluate(set())[:-1]
    with pytest.raises(ValueError, match="set mismatch"):
        build_evidence_report(fixture.lifecycle, freshness)


def test_report_rejects_current_evidence_with_stale_roots():
    fixture = build_opencadaver_verified_fixture()
    freshness = list(ProvenanceFreshness(fixture.graph).evaluate(set()))
    freshness[0] = replace(freshness[0], stale_roots=(fixture.source_id,))
    with pytest.raises(ValueError, match="current evidence"):
        build_evidence_report(fixture.lifecycle, tuple(freshness))


def test_report_rejects_stale_without_roots():
    fixture = build_opencadaver_verified_fixture()
    freshness = list(ProvenanceFreshness(fixture.graph).evaluate(set()))
    freshness[0] = EvidenceFreshness(freshness[0].evidence_id, Freshness.STALE)
    with pytest.raises(ValueError, match="requires stale roots"):
        build_evidence_report(fixture.lifecycle, tuple(freshness))


def test_tampered_identity_is_rejected_on_load():
    fixture = build_opencadaver_verified_fixture()
    report = build_evidence_report(
        fixture.lifecycle, ProvenanceFreshness(fixture.graph).evaluate(set()))
    payload = json.loads(report.canonical_json())
    payload["records"][0]["identity"]["dependency_digest"] = "tampered"
    with pytest.raises(ValueError, match="sha256"):
        EvidenceReport.from_json(json.dumps(payload))


def test_record_order_is_canonical_not_input_order():
    fixture = build_opencadaver_verified_fixture()
    freshness = ProvenanceFreshness(fixture.graph).evaluate(set())
    forward = build_evidence_report(fixture.lifecycle, freshness)
    reverse = build_evidence_report(tuple(reversed(fixture.lifecycle)), tuple(reversed(freshness)))
    assert forward.canonical_json() == reverse.canonical_json()
    assert forward.digest() == reverse.digest()
