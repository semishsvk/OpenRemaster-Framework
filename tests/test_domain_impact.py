from openremaster.domains import Domain
from openremaster.impact_rules import analyze_domains

def test_geometry_change_reaches_runtime_chain():
    plan = analyze_domains({Domain.GEOMETRY})
    assert Domain.MOVEMENT in plan.invalidated
    assert Domain.TRANSITIONS in plan.invalidated
    assert Domain.PUZZLES in plan.invalidated
    assert Domain.SAVE_LOAD in plan.invalidated
    assert Domain.E2E in plan.invalidated

def test_localization_change_does_not_invalidate_geometry():
    plan = analyze_domains({Domain.LOCALIZATION})
    assert Domain.E2E in plan.invalidated
    assert Domain.GEOMETRY not in plan.invalidated

def test_audio_change_is_narrow():
    plan = analyze_domains({Domain.AUDIO})
    assert plan.invalidated == frozenset({Domain.AUDIO, Domain.E2E})
