from openremaster.domains import Domain
from openremaster.impact_rules import analyze_domains
from openremaster.policy import choose_validation_policy

def test_audio_does_not_require_verify():
    policy = choose_validation_policy(analyze_domains({Domain.AUDIO}))
    assert policy.fast_required
    assert not policy.verify_recommended

def test_geometry_recommends_verify():
    policy = choose_validation_policy(analyze_domains({Domain.GEOMETRY}))
    assert policy.fast_required
    assert policy.verify_recommended
