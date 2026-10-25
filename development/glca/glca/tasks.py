"""Evidence-driven task ordering for the existing scheduler to consume as advice."""
from .core import require, digest

TESTS_BY_IMPACT = {
    'inventory': ['ownership', 'capacity', 'critical-item-loss', 'save-load'],
    'actor': ['actor-handoff', 'stranded-character', 'save-load'],
    'transition': ['room-transition', 'door-state', 'interaction-reachability'],
    'timer': ['timed-opportunity', 'script-scheduler', 'save-load'],
    'script': ['dependency-cycle', 'irreversible-puzzle', 'completion-predicate'],
    'camera': ['interaction-reachability', 'camera-fidelity'],
    'save': ['save-load', 'ownership', 'actor-handoff', 'timer-restore'],
    'ending': ['completion-predicate', 'false-victory', 'alternative-endings'],
}


def propose_tests(project, impacts, evidence_digest):
    require(type(project) is str and bool(project), 'PROJECT_REQUIRED')
    require(set(impacts) <= TESTS_BY_IMPACT.keys(), 'UNKNOWN_IMPACT')
    require(type(evidence_digest) is str and len(evidence_digest) == 64 and
            all(c in '0123456789abcdef' for c in evidence_digest), 'EVIDENCE_DIGEST_REQUIRED')
    tests = sorted({test for impact in impacts for test in TESTS_BY_IMPACT[impact]})
    return {'project': project, 'tests': tests, 'evidence_digest': evidence_digest,
            'proposal_digest': digest([project, sorted(impacts), evidence_digest]),
            'may_dispatch': False, 'fidelity_accepted': False}


def dependency_order(project, tasks, completed=()):
    require(len(tasks) <= 1024, 'TASK_BOUND')
    require(all(t.get('project') == project for t in tasks), 'CROSS_PROJECT_TASK')
    by_id = {t['id']: t for t in tasks}
    require(len(by_id) == len(tasks), 'DUPLICATE_TASK')
    done = set(completed)
    require(all(set(t['depends']) <= by_id.keys() | done for t in tasks), 'MISSING_TASK_DEPENDENCY')
    remaining = set(by_id) - done
    ordered, ready = [], sorted(i for i in remaining if set(by_id[i]['depends']) <= done)
    first_ready = list(ready)
    while ready:
        ident = ready.pop(0)
        remaining.remove(ident)
        done.add(ident)
        ordered.append(ident)
        ready = sorted(i for i in remaining if set(by_id[i]['depends']) <= done)
    require(not remaining, 'DEPENDENCY_CYCLE')
    return {'project': project, 'ordered': ordered, 'dependency_ready': first_ready,
            'status': 'HOLD_ADMISSION_REQUIRED', 'may_dispatch': False}
