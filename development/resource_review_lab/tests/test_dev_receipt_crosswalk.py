import unittest
from dev_receipt_crosswalk import observe

class ReceiptCrosswalkTests(unittest.TestCase):
    def test_development_commit_does_not_imply_verified_release(self):
        d={'schema':'OpenRemaster.DevWorkflowResult.v1','state':'COMMITTED','production_go':False,
           'operation_id':'test-operation','worker':{'success':True,'artifacts':{'profile':'DEV_UNSIGNED'}}}
        r=observe(d)
        self.assertEqual(r['status'],'OBSERVED_COMMITTED_DEV_ONLY')
        self.assertIs(r['release_eligible'],False)
        self.assertEqual(r['decision']['decision'],'HOLD')
        self.assertIn('IMMUTABLE_COMMIT_REQUIRED',r['decision']['reasons'])
    def test_attempt_to_inherit_production_trust_is_held(self):
        r=observe({'schema':'OpenRemaster.DevWorkflowResult.v1','state':'COMMITTED','production_go':True})
        self.assertEqual(r['status'],'HOLD_INCOMPLETE_DEV_RESULT')
        self.assertIs(r['release_eligible'],False)
    def test_unknown_receipts_rejected(self):
        for d in [None,[],{},dict(schema='Other')]:self.assertEqual(observe(d)['status'],'REJECT')
