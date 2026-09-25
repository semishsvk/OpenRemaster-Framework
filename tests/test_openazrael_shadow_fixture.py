from openremaster.change_classifier import classify_paths
from openremaster.domains import Domain
from openremaster.impact_rules import analyze_domains
from openremaster.policy import choose_validation_policy
from openremaster.testplan import plan_tests

OPENAZRAEL_FLOOR_FIX_PATHS = [
    "OPENAZRAEL_CONTEXT.md",
    "README.md",
    "data/project_context.json",
    "data/tests/kg001_candidate_diagnostics_contract_v116.json",
    "scripts/candidate_diagnostics_v116.gd",
    "scripts/kg001_room_trigger_runner_v110.gd",
    "scripts/room_manager.gd",
    "tools/validate_candidate_diagnostics_v116.py",
    "tools/validate_kg001_room_trigger_v110.py",
]

def test_historical_floor_fix_shadow_plan():
    # Commit 356dddf... fixed falling through legacy room floors.
    # Commit message supplies semantic geometry intent where generic path
    # classification alone is intentionally conservative.
    direct = set(classify_paths(OPENAZRAEL_FLOOR_FIX_PATHS))
    direct.add(Domain.GEOMETRY)
    impact = analyze_domains(direct)
    policy = choose_validation_policy(impact)
    fast = plan_tests(impact)
    verify = plan_tests(impact, include_verify=True)

    assert policy.verify_recommended
    assert "geometry-validation" in fast.ids
    assert "movement-collision" in fast.ids
    assert "transition-contracts" in fast.ids
    assert "save-load-contracts" in fast.ids
    assert "runtime-integration" in verify.ids
    assert "e2e-playthrough" in verify.ids
