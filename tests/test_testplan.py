from openremaster.domains import Domain
from openremaster.impact_rules import analyze_domains
from openremaster.testplan import plan_tests

def test_audio_fast_plan_is_minimal():
    plan = plan_tests(analyze_domains({Domain.AUDIO}))
    assert plan.ids == ("audio-events",)

def test_geometry_fast_plan_covers_transitive_impact():
    plan = plan_tests(analyze_domains({Domain.GEOMETRY}))
    assert "geometry-validation" in plan.ids
    assert "movement-collision" in plan.ids
    assert "transition-contracts" in plan.ids
    assert "puzzle-units" in plan.ids
    assert "save-load-contracts" in plan.ids
    assert "e2e-playthrough" not in plan.ids

def test_verify_adds_runtime_and_e2e():
    plan = plan_tests(analyze_domains({Domain.GEOMETRY}), include_verify=True)
    assert "runtime-integration" in plan.ids
    assert "e2e-playthrough" in plan.ids
