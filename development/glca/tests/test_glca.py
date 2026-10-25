import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from glca.core import (CLASSES, STATUSES, Hold, read_pinned, reachability,
                       validate_finding, state_roundtrip, shadow_proposal, production_gate)
from glca.source import decoded_cfg, reverse_script_dependencies
from glca.replay import diagnose

ROOT = Path(__file__).resolve().parent.parent


class GraphTests(unittest.TestCase):
    def graph(self, edges, endings=('win',), complete=False, limit=4096):
        return reachability(['start', 'left', 'right', 'trap', 'win'],
                            [{'from': a, 'to': b, 'guard': g} for a, b, g in edges],
                            'start', endings, complete=complete, limit=limit)

    def test_alternative_legal_model_paths(self):
        result = self.graph([('start', 'left', True), ('start', 'right', True),
                             ('left', 'win', True), ('right', 'win', True)], complete=True)
        self.assertEqual(result['recoverable'], ['left', 'right', 'start', 'win'])
        self.assertFalse(result['original_game_validated'])

    def test_irreversible_trap_is_candidate(self):
        result = self.graph([('start', 'trap', True)], complete=True)
        self.assertIn('trap', result['dead_end_candidates'])
        self.assertEqual(result['confirmed_softlocks'], 0)

    def test_unknown_escape_not_hard_softlock(self):
        result = self.graph([('start', 'trap', True), ('trap', 'win', None)], complete=True)
        self.assertEqual(result['status'], 'HOLD')
        self.assertNotIn('trap', result['dead_end_candidates'])

    def test_unknown_guard_does_not_prove_reachability(self):
        self.assertEqual(self.graph([('start', 'win', None)])['unproven'], ['win'])

    def test_unknown_victory_not_full_coverage(self):
        result = self.graph([], endings=(), complete=True)
        self.assertEqual(result['status'], 'HOLD')
        self.assertEqual(result['dead_end_candidates'], [])

    def test_false_guard_excluded(self):
        self.assertNotIn('win', self.graph([('start', 'win', False)])['possibly_reachable'])

    def test_cycle_terminates(self):
        self.assertEqual(self.graph([('start', 'left', True), ('left', 'start', True)])['reachable'], ['left', 'start'])

    def test_invalid_guard(self):
        with self.assertRaisesRegex(Hold, 'GUARD'):
            self.graph([('start', 'win', 'true')])

    def test_bound_rejected(self):
        with self.assertRaisesRegex(Hold, 'BOUND'):
            self.graph([], limit=2)

    def test_dangling_state(self):
        with self.assertRaisesRegex(Hold, 'DANGLING'):
            self.graph([('start', 'other-game', True)])


class EvidenceTests(unittest.TestCase):
    def finding(self):
        return {'class': 'SL-01', 'status': 'STATIC_CANDIDATE', 'project': 'SYNTHETIC',
                'game_version': 'fixture-v1', 'source_sha256': 'a' * 64,
                'location': {'room': 'fixture-room', 'actor': 'UNKNOWN'}, 'unknowns': ['VICTORY']}

    def test_all_twelve_classes(self):
        self.assertEqual(len(CLASSES), 12)
        for key in CLASSES:
            with self.subTest(key=key):
                finding = self.finding()
                finding['class'] = key
                self.assertFalse(validate_finding(finding)['hard_softlock_proven'])

    def test_all_statuses_explicit(self):
        self.assertEqual(len(STATUSES), 8)

    def test_static_to_confirmed_rejected(self):
        for status in STATUSES - {'STATIC_CANDIDATE', 'UNRESOLVED', 'HOLD'}:
            with self.subTest(status=status):
                finding = {**self.finding(), 'status': status, 'independent_verifier': True,
                           'runtime_verified': True, 'screenshot': 'fake.png'}
                with self.assertRaisesRegex(Hold, 'VERIFIER'):
                    validate_finding(finding)

    def test_static_proof_boolean_rejected(self):
        with self.assertRaisesRegex(Hold, 'PROMOTION'):
            validate_finding({**self.finding(), 'unwinnable_proven': True})

    def test_unknown_actor_preserved(self):
        finding = self.finding()
        validate_finding(finding)
        self.assertEqual(finding['location']['actor'], 'UNKNOWN')

    def test_bad_source_digest(self):
        with self.assertRaisesRegex(Hold, 'SOURCE_HASH'):
            validate_finding({**self.finding(), 'source_sha256': 'guessed'})

    def test_pin_drift(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / 'drift.json'
            path.write_text('{}')
            with self.assertRaisesRegex(Hold, 'DRIFT'):
                read_pinned(path, '0' * 64)

    def test_duplicate_json_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / 'duplicate.json'
            path.write_bytes(b'{"x":1,"x":2}')
            with self.assertRaisesRegex(Hold, 'DUPLICATE'):
                read_pinned(path, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_dev_cannot_release_even_with_forged_attestation(self):
        self.assertFalse(production_gate({'worker': 'PRODUCTION', 'signed': True,
                                         'owner': True, 'independent': True})['may_release'])

    def test_conflicting_owner_cannot_dispatch(self):
        result = shadow_proposal('SYNTHETIC', 'checkpoint', [], [], 'NORMAL')
        self.assertFalse(result['may_dispatch'])
        self.assertIn('SINGLE_WRITER', result['required_admission'])

    def test_dependency_resolution(self):
        result = shadow_proposal('SYNTHETIC', 'checkpoint', ['GLCA-001', 'GLCA-002'], ['GLCA-001'])
        self.assertEqual(result['missing_dependencies'], ['GLCA-002'])

    def test_gaming_no_heavy_admission(self):
        for mode in ('GAMING', 'LIGHT', 'UNKNOWN'):
            with self.subTest(mode=mode):
                result = shadow_proposal('SYNTHETIC', 'c', [], [], mode)
                self.assertEqual(result['budget']['heavy_slots_requested'], 0)
                self.assertFalse(result['may_acquire_lease'])

    def test_missing_save_roundtrip(self):
        with self.assertRaisesRegex(Hold, 'INCOMPLETE_SAVE'):
            state_roundtrip({}, {})

    def test_state_losses_and_handoffs_detected(self):
        before = dict(actors={'Zak': 1}, inventory={'key': 'Zak'}, timers={'door': 5},
                      scripts={'terminal': 'waiting'}, rooms={'door': 'open'}, globals={'won': False}, camera={'room': 1})
        self.assertEqual(state_roundtrip(before, copy.deepcopy(before))['status'], 'PASS')
        for field in before:
            with self.subTest(field=field):
                after = {**before, field: {}}
                self.assertEqual(state_roundtrip(before, after)['differences'], [field])


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.original = {'schema': 'OpenRemaster.BehaviorTraceDocument.v1', 'project': 'SYNTHETIC',
                         'corpus_sha256': 'a' * 64, 'capture_point': 'synthetic-only', 'witness_sha256': 'b' * 64,
                         'events': [{'tick': i, 'kind': k, 'effect': 'fixture'} for i, k in enumerate(
                             ['INPUT', 'HANDLER', 'STATE', 'ANIMATION', 'INVENTORY', 'AUDIO', 'TRANSITION', 'SAVE_LOAD'])]}
        self.candidate = copy.deepcopy(self.original)

    def call(self):
        a, b = (json.dumps(d).encode() for d in (self.original, self.candidate))
        return diagnose(a, b, hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest(),
                        {k: self.original[k] for k in ('project', 'corpus_sha256', 'capture_point')})

    def test_matching_synthetic_events_never_fidelity(self):
        result = self.call()
        self.assertEqual(result['reason'], 'PROVIDED_EVENTS_MATCH')
        self.assertFalse(result['can_claim_fidelity_verified'])

    def test_earliest_mismatch_before_later_failure(self):
        self.candidate['events'][2]['effect'] = 'wrong-state'
        self.candidate['events'][6]['effect'] = 'broken-door'
        result = self.call()
        self.assertEqual(result['first_difference']['index'], 2)
        self.assertFalse(result['root_cause_proven'])

    def test_timing_divergence(self):
        for event in self.candidate['events']:
            event['tick'] += 1
        self.assertEqual(self.call()['first_difference']['index'], 0)

    def test_screenshot_not_trace(self):
        self.candidate = {'screenshot': 'fixture.png'}
        self.assertEqual(self.call()['reason'], 'TRACE_SCHEMA')

    def test_missing_save_trace_rejected(self):
        self.original['events'].pop()
        self.assertEqual(self.call()['reason'], 'ORIGINAL_BEHAVIOR_COVERAGE_INSUFFICIENT')

    def test_cross_project_trace_rejected(self):
        self.candidate['project'] = 'OTHER'
        self.assertEqual(self.call()['reason'], 'IDENTITY_MISMATCH')


class SourceTests(unittest.TestCase):
    def test_partial_cfg_preserves_unknown_branches(self):
        programs = [{'key': 'SYNTHETIC', 'status': 'PARTIAL', 'bytes': 5, 'instructions': [
            {'pc': 0, 'end_pc': 2, 'kind': 'compare', 'operands': {'branch_to_pc': 4}},
            {'pc': 2, 'end_pc': 3, 'kind': 'stopObjectCode', 'operands': {}}]}]
        cfg = decoded_cfg(programs)
        self.assertTrue(cfg['unknowns'])
        self.assertTrue(all(e['guard'] is None for e in cfg['edges']))
        self.assertEqual(cfg['victory_predicate'], 'UNKNOWN')

    def test_call_dependencies_not_proven_paths(self):
        programs = [{'key': 'SC1', 'instructions': [{'kind': 'startScript', 'operands': {'script': {'direct': 2}}}]}]
        result = reverse_script_dependencies(programs, ['SC2'])
        self.assertEqual(result['possible_prerequisite_programs'], ['SC1', 'SC2'])
        self.assertFalse(result['legal_completion_path_proven'])


if __name__ == '__main__':
    unittest.main()
