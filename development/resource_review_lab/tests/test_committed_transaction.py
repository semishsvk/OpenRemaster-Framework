import copy,hashlib,json,unittest
from admission_boundary_base import canonical
from proposal_commitment import DOMAIN,intent_digest
from committed_resource_check import prepare_committed_resource_check
import test_resource_transaction as fixture
import test_binding as binding_fixture
import resource_authority as authority

class CommittedTransactionTests(unittest.TestCase):
    def setUp(self):
        self.t=fixture.ResourceTransactionTests(methodName='test_atomic_ack_binds_resource_and_reopens');self.t.setUp();self.addCleanup(self.t.doCleanups)
        t=self.t;t.f.binding['project']='OpenRemasterStudio';t.f.context['project_id']='OpenRemasterStudio'
        job=json.loads(t.f.job);job['project']='OpenRemasterStudio';t.f.job=canonical(job);t.f.binding['job_sha256']=hashlib.sha256(t.f.job).hexdigest();t.f.resign();t.refresh();t.store.activate_owner(t.f.grant,now=t.f.now)
        b=binding_fixture.BindingTests(methodName='test_bound_is_still_hold');b.setUp();self.pins=copy.deepcopy(b.pins);self.proposal=copy.deepcopy(b.proposal)
        p=self.proposal;f=t.f;c=f.context;e=t.case.expected;d=lambda v:hashlib.sha256(canonical(v)).hexdigest()
        p.update(operation_id=f.binding['operation_id'],source_manifest_sha256=f.binding['source_sha256'],request_sha256=d(f.request),job_bytes_sha256=hashlib.sha256(f.job).hexdigest(),owner_fence_sha256=d(dict(owner_id=f.binding['owner_id'],owner_epoch=f.binding['owner_epoch'],lease_id=f.binding['lease_id'],fence_generation=f.binding['fence_generation'])),resource_fence_sha256=d(dict(authority_id=e['authority_id'],source_id=e['source_id'],policy_version=c['policy_version'],resource_fence=c['resource_fence'])))
        job['development_intent']=dict(schema=DOMAIN,intent_sha256=intent_digest(p));f.job=canonical(job);f.binding['job_sha256']=hashlib.sha256(f.job).hexdigest();f.resign();t.refresh();p['job_bytes_sha256']=hashlib.sha256(f.job).hexdigest()
    def check(self):
        t=self.t
        return prepare_committed_resource_check(self.proposal,t.case.inputs,t.case.obs,expected_identity=t.f.expected,expected_resource=t.case.expected,recipe_pins=self.pins,owner_keys={'owner-fixture':t.f.owner},envelope_keys={'ed-fixture':t.f.public})
    def test_atomic_claim_ack_event_preserve_signed_job_commitment(self):
        t=self.t;ack=t.admit(resource_check=self.check());self.assertFalse(ack['may_dispatch']);self.assertEqual(ack['job_sha256'],self.proposal['job_bytes_sha256']);self.assertEqual(t.counts(),[1]*4);t.store.audit()
        self.assertEqual(t.open().lookup(t.f.binding['operation_id'])['ack'],ack)
    def test_mutated_intent_never_reserves_resource(self):
        self.proposal['timeout_seconds']=1200
        with self.assertRaisesRegex(authority.Hold,'SIGNED_JOB_INTENT_MISMATCH'):self.t.admit(resource_check=self.check())
        self.assertEqual(self.t.counts(),[0]*4);self.assertEqual(self.t.highwater(),10)
    def test_caller_mutation_after_preparation_cannot_rebind(self):
        callback=self.check();self.proposal['timeout_seconds']=1200
        self.assertFalse(self.t.admit(resource_check=callback)['may_dispatch'])
    def test_replay_retains_query_only(self):
        callback=self.check();self.t.admit(resource_check=callback)
        with self.assertRaisesRegex(authority.Hold,'QUERY_ONLY'):self.t.admit(resource_check=callback)
        self.assertEqual(self.t.counts(),[1]*4)
    def test_owner_loss_after_preparation_blocks_commitment(self):
        callback=self.check()
        with self.t.store.connect() as db:db.execute("UPDATE owners SET status='RELEASED'")
        with self.assertRaises(authority.Hold):self.t.admit(resource_check=callback)
        self.assertEqual(self.t.counts(),[0]*4)
    def test_resource_fence_after_preparation_blocks(self):
        callback=self.check()
        with self.t.store.connect() as db:db.execute('UPDATE resource_state SET fence=4')
        with self.assertRaisesRegex(authority.Hold,'FENCE_OR_POLICY'):self.t.admit(resource_check=callback)
        self.assertEqual(self.t.counts(),[0]*4)
    def test_failure_after_resource_reservation_rolls_back(self):
        def fault(point):
            if point=='AFTER_RESOURCE_RESERVATION':raise RuntimeError('synthetic')
        with self.assertRaises(RuntimeError):self.t.admit(resource_check=self.check(),inject_fault=fault)
        self.assertEqual(self.t.counts(),[0]*4);self.assertEqual(self.t.highwater(),10);self.t.store.audit()
    def test_precomputed_report_cannot_replace_inputs(self):
        self.t.case.inputs={'commitment_checks_satisfied':True}
        with self.assertRaises((KeyError,authority.Hold)):self.t.admit(resource_check=self.check())
        self.assertEqual(self.t.counts(),[0]*4)
