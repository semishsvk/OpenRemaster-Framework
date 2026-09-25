import json
from openremaster.cache import CacheDecision
from openremaster.domains import Domain
from openremaster.impact_rules import analyze_domains
from openremaster.policy import choose_validation_policy
from openremaster.provenance import build_provenance, provenance_json
from openremaster.report import invalidation_report
from openremaster.reuse import PlannedCheck

def test_provenance_binds_reuse_to_sha_and_digest():
    check = PlannedCheck("audio-events", CacheDecision.REUSE, "exact immutable identity match")
    record = build_provenance(check, "openazrael", "abc123", "digest1", "runner", "1")
    assert record.source_revision == "abc123"
    assert record.input_digest == "digest1"
    assert record.evidence_id is not None

def test_report_is_deterministic_json():
    impact = analyze_domains({Domain.AUDIO})
    policy = choose_validation_policy(impact)
    record = build_provenance(
        PlannedCheck("audio-events", CacheDecision.RERUN, "identity miss"),
        "p", "sha", "digest", "runner", "1"
    )
    report1 = invalidation_report(impact, policy, (record,))
    report2 = invalidation_report(impact, policy, (record,))
    assert report1 == report2
    parsed = json.loads(report1)
    assert parsed["invalidated_domains"] == ["audio", "e2e"]
