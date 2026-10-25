import unittest
from glca.core import Hold
from glca.tasks import dependency_order, propose_tests


class TaskTests(unittest.TestCase):
    def test_topological_resolution(self):
        tasks = [{'id': i, 'project': 'fixture', 'depends': deps} for i, deps in
                 [('replay', ['world']), ('world', []), ('gate', ['replay'])]]
        result = dependency_order('fixture', tasks)
        self.assertEqual(result['ordered'], ['world', 'replay', 'gate'])
        self.assertEqual(result['dependency_ready'], ['world'])
        self.assertFalse(result['may_dispatch'])

    def test_cycle_rejected_before_admission(self):
        with self.assertRaisesRegex(Hold, 'DEPENDENCY_CYCLE'):
            dependency_order('fixture', [{'id': 'a', 'project': 'fixture', 'depends': ['b']},
                                         {'id': 'b', 'project': 'fixture', 'depends': ['a']}])

    def test_missing_dependency(self):
        with self.assertRaisesRegex(Hold, 'MISSING_TASK_DEPENDENCY'):
            dependency_order('fixture', [{'id': 'a', 'project': 'fixture', 'depends': ['missing']}])

    def test_project_isolation(self):
        with self.assertRaisesRegex(Hold, 'CROSS_PROJECT_TASK'):
            dependency_order('fixture', [{'id': 'a', 'project': 'foreign', 'depends': []}])

    def test_evidence_driven_selection(self):
        selected = propose_tests('fixture', ['inventory', 'timer'], 'a' * 64)
        self.assertIn('critical-item-loss', selected['tests'])
        self.assertIn('timed-opportunity', selected['tests'])
        self.assertNotIn('camera-fidelity', selected['tests'])
        self.assertFalse(selected['may_dispatch'])

    def test_evidence_change_invalidates_proposal(self):
        first = propose_tests('fixture', ['save'], 'a' * 64)
        second = propose_tests('fixture', ['save'], 'b' * 64)
        self.assertNotEqual(first['proposal_digest'], second['proposal_digest'])

    def test_unknown_impact_not_silently_ignored(self):
        with self.assertRaisesRegex(Hold, 'UNKNOWN_IMPACT'):
            propose_tests('fixture', ['guessed'], 'a' * 64)


if __name__ == '__main__':
    unittest.main()
