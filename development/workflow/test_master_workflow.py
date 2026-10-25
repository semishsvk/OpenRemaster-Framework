import unittest
from glca.core import Hold
from master_workflow import advisory_package,RLR_TO_GLCA

class MasterWorkflowTests(unittest.TestCase):
    def tasks(self):return [dict(id='decode',project='fixture',depends=[]),dict(id='atlas',project='fixture',depends=['decode'])]
    def call(self,**kwargs):return advisory_package('fixture',self.tasks(),[],['script'],'a'*64,**kwargs)
    def test_existing_glca_plan_reused_no_dispatch(self):
        r=self.call();self.assertEqual(r['dependency_plan']['dependency_ready'],['decode'])
        self.assertEqual(r['executor'],'EXISTING_K003_ONLY');self.assertFalse(r['may_dispatch'])
    def test_all_nine_rlr_packages_mapped(self):self.assertEqual(set(RLR_TO_GLCA),{f'RLR-{i:02}' for i in range(1,10)})
    def test_governor_modes_never_grant_heavy_slot(self):
        for mode in ('NORMAL','GAME','GAMING','LIGHT','UNKNOWN'):
            r=self.call(governor_mode=mode);self.assertEqual(r['resource_request']['heavy_slots'],0)
    def test_project_conflict_rejected(self):
        with self.assertRaises(Hold):advisory_package('foreign',self.tasks(),[],['script'],'a'*64)
    def test_source_change_invalidates_proposal(self):
        a=self.call();b=advisory_package('fixture',self.tasks(),[],['script'],'b'*64)
        self.assertNotEqual(a['proposal_digest'],b['proposal_digest'])
    def test_development_receipt_cannot_inherit_release(self):
        r=self.call(dev_receipt=dict(schema='OpenRemaster.DevWorkflowResult.v1',production_go=True))
        self.assertFalse(r['dev_build_observation']['release_eligible']);self.assertFalse(r['may_publish'])

if __name__=='__main__':unittest.main()
