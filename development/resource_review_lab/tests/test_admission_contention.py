"""Independent contenders share only one disposable existing authority store."""
import copy,hashlib,json,threading,unittest
from concurrent.futures import ThreadPoolExecutor
import test_resource_transaction as fixture
import resource_authority as authority
from admission_boundary_base import canonical
from resource_observation import review_resource_observation

class ContentionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ResourceTransactionTests(methodName='test_atomic_ack_binds_resource_and_reopens');self.f.setUp();self.addCleanup(self.f.doCleanups)
    def contender(self,index,*,project=None,nonce=None,sequence=11):
        t=copy.copy(self.f);t.f=copy.copy(self.f.f);t.case=copy.copy(self.f.case)
        t.f.binding=copy.deepcopy(self.f.f.binding);t.f.context=copy.deepcopy(self.f.f.context);t.f.request=copy.deepcopy(self.f.f.request)
        t.case.expected=copy.deepcopy(self.f.case.expected);t.case.obs=copy.deepcopy(self.f.case.obs)
        t.f.binding.update(operation_id=f'{index:032x}',job_id=f'contender-{index}',nonce=nonce or f'contender_nonce_{index:016x}')
        if project is not None:t.f.binding['project']=project;t.f.context['project_id']=project
        t.f.context['operation_id']=t.f.binding['operation_id'];t.f.request['operation_id']=t.f.binding['operation_id']
        job=json.loads(t.f.job);job.update(job_id=t.f.binding['job_id'],project=t.f.binding['project']);t.f.job=canonical(job)
        t.f.binding['job_sha256']=hashlib.sha256(t.f.job).hexdigest();t.f.resign();t.refresh();t.case.obs['sequence']=sequence
        return t
    def race(self,contenders):
        barrier=threading.Barrier(len(contenders),timeout=10)
        def attempt(t):
            callback=t.check();barrier.wait()
            try:
                ack=t.admit(resource_check=callback)
                return ('committed',ack)
            except authority.Hold as e:return ('held',str(e))
        with ThreadPoolExecutor(max_workers=len(contenders)) as pool:return list(pool.map(attempt,contenders))
    def assert_one(self,results):
        self.assertEqual([r[0] for r in results].count('committed'),1,results)
        self.assertEqual(self.f.counts(),[1]*4);self.assertEqual(self.f.highwater(),11)
        self.assertEqual(self.f.store.audit()['operations'],1)
        for state,value in results:
            if state=='committed':self.assertIs(value['may_dispatch'],False);self.assertIs(value['resource_claim']['production_go'],False)
    def reviewed(self,t):
        r=review_resource_observation(t.case.inputs,t.case.obs,expected_identity=t.f.expected,expected_resource=t.case.expected,owner_keys={'owner-fixture':t.f.owner},envelope_keys={'ed-fixture':t.f.public},now=t.f.now)
        self.assertTrue(r['resource_checks_satisfied'],r);self.assertFalse(r['may_dispatch'])
    def test_distinct_operations_same_project_have_one_writer(self):
        results=self.race([self.contender(i) for i in range(1,5)]);self.assert_one(results)
        self.assertTrue(all('SEQUENCE_REPLAY_OR_STALE' in value for state,value in results if state=='held'))
    def test_cross_project_same_sequence_cannot_double_reserve(self):
        contenders=[self.contender(i,project=f'SYNTHETIC_{i}') for i in range(1,5)]
        for t in contenders:t.store.activate_owner(t.f.grant,now=t.f.now)
        self.assert_one(self.race(contenders))
    def test_same_nonce_new_operation_rolls_back_new_resource_sequence(self):
        self.f.admit();t=self.contender(2,nonce=self.f.f.binding['nonce'],sequence=12)
        with self.assertRaisesRegex(authority.Hold,'NONCE_JOB_OR_OPERATION_REPLAY_CONFLICT'):t.admit()
        self.assertEqual(self.f.counts(),[1]*4);self.assertEqual(self.f.highwater(),11);self.assertEqual(self.f.store.audit()['operations'],1)
    def test_new_sequence_same_project_writer_rolls_back(self):
        self.f.admit();t=self.contender(2,sequence=12)
        with self.assertRaisesRegex(authority.Hold,'GAME_WIP_LIMIT'):t.admit()
        self.assertEqual(self.f.counts(),[1]*4);self.assertEqual(self.f.highwater(),11);self.f.store.audit()
    def test_owner_released_after_offline_review_is_rechecked(self):
        t=self.contender(1);self.reviewed(t);callback=t.check()
        with t.store.connect() as db:db.execute("UPDATE owners SET status='RELEASED'")
        with self.assertRaisesRegex(authority.Hold,'OWNER_EPOCH_GENERATION_LEASE_OR_SOURCE'):t.admit(resource_check=callback)
        self.assertEqual(t.counts(),[0]*4);self.assertEqual(t.highwater(),10);t.store.audit()
    def test_owner_generation_changed_after_review_is_rechecked(self):
        t=self.contender(1);self.reviewed(t);callback=t.check()
        with t.store.connect() as db:db.execute('UPDATE owners SET generation=2')
        with self.assertRaisesRegex(authority.Hold,'OWNER_EPOCH_GENERATION_LEASE_OR_SOURCE'):t.admit(resource_check=callback)
        self.assertEqual(t.counts(),[0]*4);self.assertEqual(t.highwater(),10)
    def test_resource_fence_changed_after_review_is_rechecked(self):
        t=self.contender(1);self.reviewed(t);callback=t.check()
        with t.store.connect() as db:db.execute('UPDATE resource_state SET fence=4')
        with self.assertRaisesRegex(authority.Hold,'FENCE_OR_POLICY_CHANGED'):t.admit(resource_check=callback)
        self.assertEqual(t.counts(),[0]*4);self.assertEqual(t.highwater(),10)
    def test_committed_operation_cannot_be_resubmitted_with_fresh_sequence(self):
        self.f.admit();self.f.case.obs['sequence']=12
        with self.assertRaisesRegex(authority.Hold,'QUERY_ONLY'):self.f.admit()
        self.assertEqual(self.f.counts(),[1]*4);self.assertEqual(self.f.highwater(),11)
        record=self.f.open().lookup(self.f.f.binding['operation_id']);self.assertFalse(record['automatic_retry']);self.f.store.audit()
