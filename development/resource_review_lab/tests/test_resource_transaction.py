import copy,hashlib,hmac,sqlite3,tempfile,unittest,secrets
from pathlib import Path
from contextlib import closing
import test_resource_observation as fixture
from admission_boundary_base import canonical
import resource_authority as a
from resource_transaction import prepare_resource_check
from concurrent.futures import ThreadPoolExecutor

class ResourceTransactionTests(unittest.TestCase):
    def setUp(self):
        self.case=fixture.ResourceObservationTests(methodName='test_normal_proposal_still_has_no_authority_or_consumption');self.case.setUp();self.f=self.case.f
        self.f.binding['fence_generation']=1;self.f.context['fence']=1;self.f.resign()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)/'lab.sqlite3';self.ackkey=secrets.token_bytes(32)
        self.refresh()
        self.store=self.open();self.store.activate_owner(self.f.grant,now=self.f.now)
        with self.store.connect() as db:db.execute('INSERT INTO resource_state VALUES(?,?,?,?,?)',('synthetic-resource','synthetic-telemetry',3,'synthetic-policy',10))
    def signer(self,body):
        b=dict(body,key_id='ack-fixture');b['signature']=hmac.new(self.ackkey,a.canonical(b),hashlib.sha256).hexdigest();return b
    def open(self):return a.LocalAuthorityCandidate(self.path,self.temp.name,{'owner-fixture':self.f.owner},{'ack-fixture':self.ackkey},self.signer,isolated_lab=True)
    def refresh(self):
        self.f.expected=dict(binding=copy.deepcopy(self.f.binding),shadow_context=copy.deepcopy(self.f.context))
        digest=hashlib.sha256(canonical(self.f.call())).hexdigest()
        self.case.inputs=dict(envelope=self.f.envelope,request=self.f.request,grant=self.f.grant,poa_request=self.f.poa_request,job_bytes=self.f.job)
        self.case.expected.update(owner_fence=1,work_identity_sha256=digest)
        self.case.obs.update(owner_fence=1,work_identity_sha256=digest,project_id=self.f.binding['project'],operation_id=self.f.binding['operation_id'],jobs=[self.case.job(self.f.binding['job_id'])])
    def check(self):return prepare_resource_check(self.case.inputs,self.case.obs,expected_identity=self.f.expected,expected_resource=self.case.expected,owner_keys={'owner-fixture':self.f.owner},envelope_keys={'ed-fixture':self.f.public})
    def admit(self,**kw):
        args=dict(now=self.f.now,clock=lambda:self.f.now,resource_check=self.check());args.update(kw)
        return self.store.admit(self.f.grant,self.f.poa_request,self.f.job,**args)
    def counts(self):
        with self.store.connect() as db:return [db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ('operations','nonce_claim','outbox','resource_claims')]
    def highwater(self):
        with self.store.connect() as db:return db.execute('SELECT last_sequence FROM resource_state').fetchone()[0]
    def test_atomic_ack_binds_resource_and_reopens(self):
        ack=self.admit();self.assertFalse(ack['may_dispatch']);self.assertEqual(self.counts(),[1]*4);self.assertEqual(self.highwater(),11)
        self.assertFalse(ack['resource_claim']['independent_resource_authority_verified'])
        self.assertEqual(self.open().lookup(self.f.binding['operation_id'])['ack'],ack)
        self.assertEqual(self.store.audit()['operations'],1)
    def test_every_precommit_fault_rolls_back_resource_and_nonce(self):
        for point in ('AFTER_RESOURCE_RESERVATION','AFTER_NONCE_BEFORE_OUTBOX','AFTER_OUTBOX_BEFORE_EVENT','BEFORE_LOCAL_COMMIT'):
            def fault(current):
                if current==point:raise RuntimeError(point)
            with self.assertRaises(RuntimeError):self.admit(inject_fault=fault)
            self.assertEqual(self.counts(),[0]*4,point);self.assertEqual(self.highwater(),10)
            self.assertEqual(self.store.audit()['operations'],0)
    def test_postcommit_response_loss_is_query_only(self):
        def fault(point):
            if point=='AFTER_LOCAL_COMMIT_BEFORE_REPLY':raise RuntimeError('response lost')
        with self.assertRaises(RuntimeError):self.admit(inject_fault=fault)
        self.assertEqual(self.counts(),[1]*4);record=self.open().lookup(self.f.binding['operation_id']);self.assertFalse(record['automatic_retry'])
        with self.assertRaisesRegex(a.Hold,'QUERY_ONLY'):self.admit()
        self.assertEqual(self.counts(),[1]*4)
    def test_expiry_resampled_after_lock(self):
        with self.assertRaises(a.Hold):self.admit(clock=lambda:self.f.now+100)
        self.assertEqual(self.counts(),[0]*4)
    def test_observation_expiry_after_lock_holds(self):
        with self.assertRaisesRegex(a.Hold,'STALE_OR_INVALID_INTERVAL'):self.admit(clock=lambda:self.f.now+5)
        self.assertEqual(self.highwater(),10)
    def test_changed_resource_fence_or_policy_rejects(self):
        for column,value in [('fence',4),('policy','new-policy')]:
            with self.store.connect() as db:db.execute('UPDATE resource_state SET '+column+'=?',(value,))
            with self.assertRaisesRegex(a.Hold,'FENCE_OR_POLICY'):self.admit()
            with self.store.connect() as db:db.execute('UPDATE resource_state SET fence=3,policy=?',('synthetic-policy',))
        self.assertEqual(self.counts(),[0]*4)
    def test_owner_lease_loss_rejects_before_resource_consumption(self):
        with self.store.connect() as db:db.execute("UPDATE owners SET status='RELEASED'")
        with self.assertRaises(a.Hold):self.admit()
        self.assertEqual(self.highwater(),10);self.assertEqual(self.counts(),[0]*4)
    def test_missing_resource_state_holds(self):
        with self.store.connect() as db:db.execute('DELETE FROM resource_state')
        with self.assertRaisesRegex(a.Hold,'RESOURCE_AUTHORITY_UNAVAILABLE'):self.admit()
        self.assertEqual(self.counts(),[0]*4)
    def test_no_resource_or_clock_fallback(self):
        with self.assertRaises(a.Hold):self.admit(resource_check=None)
        with self.assertRaises(a.Hold):self.admit(clock=None)
        self.assertEqual(self.counts(),[0]*4)
    def test_reused_sequence_with_changed_operation_or_project_rejects(self):
        self.admit()
        for project in ('SYNTHETIC','FOREIGN'):
            self.f.binding.update(operation_id='e'*32,nonce='synthetic_other_nonce_0123',job_id='other-job',project=project)
            self.f.context.update(operation_id='e'*32,project_id=project);self.f.request['operation_id']='e'*32
            self.f.job=canonical(dict(schema='ORCH-K003.Job.v1',job_id='other-job',project=project,task='test-only'))
            self.f.binding['job_sha256']=hashlib.sha256(self.f.job).hexdigest();self.f.resign();self.refresh()
            self.store.activate_owner(self.f.grant,now=self.f.now)
            with self.assertRaisesRegex(a.Hold,'SEQUENCE_REPLAY_OR_STALE'):self.admit()
        self.assertEqual(self.counts(),[1]*4)
    def test_tampered_resource_row_rejected_on_lookup(self):
        self.admit()
        with self.store.connect() as db:db.execute("UPDATE resource_claims SET claim_json='{}'")
        with self.assertRaisesRegex(a.Hold,'RESOURCE_LOOKUP'):self.store.lookup(self.f.binding['operation_id'])
        with self.assertRaises(a.Hold):self.store.audit()
    def test_foreign_existing_database_is_not_migrated(self):
        other=Path(self.temp.name)/'foreign.sqlite3'
        with closing(sqlite3.connect(other)) as db:db.execute('CREATE TABLE foreign_data(x)');db.commit()
        before=other.read_bytes()
        with self.assertRaisesRegex(a.Hold,'FOREIGN_DATABASE'):a.LocalAuthorityCandidate(other,self.temp.name,{'owner-fixture':self.f.owner},{'ack-fixture':self.ackkey},self.signer,isolated_lab=True)
        self.assertEqual(other.read_bytes(),before)
    def test_explicit_disposable_flag_required(self):
        with self.assertRaisesRegex(a.Hold,'DISPOSABLE_LAB'):a.LocalAuthorityCandidate(self.path,self.temp.name,{}, {},self.signer)
    def test_game_and_unknown_hold_before_resource_write(self):
        self.case.obs['telemetry']['game_detected']=True
        with self.assertRaisesRegex(a.Hold,'GOVERNOR_LIGHT'):self.admit()
        self.case.obs['telemetry']['game_detected']=False;self.case.obs['jobs'].append(self.case.job('unknown',state='UNKNOWN'))
        with self.assertRaisesRegex(a.Hold,'UNKNOWN_EXECUTION'):self.admit()
        self.assertEqual(self.highwater(),10)
    def test_fourth_heavy_not_reserved(self):
        self.case.obs['jobs']=[self.case.job(str(i),state='RUNNING') for i in range(3)]+[self.case.job(self.f.binding['job_id'])]
        with self.assertRaisesRegex(a.Hold,'CAPACITY_OR_GOVERNOR'):self.admit()
        self.assertEqual(self.counts(),[0]*4)
    def test_concurrent_operation_has_one_commit_and_no_automatic_reexecution(self):
        def attempt(_):
            try:self.admit();return 'committed'
            except a.Hold:return 'held'
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(attempt,range(8)))
        self.assertEqual(results.count('committed'),1);self.assertEqual(self.counts(),[1]*4);self.assertEqual(self.highwater(),11)
    def test_existing_project_writer_blocks_and_rolls_resource_back(self):
        self.admit()
        self.f.binding.update(operation_id='e'*32,nonce='synthetic_other_nonce_0123',job_id='other-job')
        self.f.context['operation_id']='e'*32;self.f.request['operation_id']='e'*32
        self.f.job=canonical(dict(schema='ORCH-K003.Job.v1',job_id='other-job',project='SYNTHETIC',task='test-only'))
        self.f.binding['job_sha256']=hashlib.sha256(self.f.job).hexdigest();self.f.resign();self.refresh();self.case.obs['sequence']=12
        with self.assertRaisesRegex(a.Hold,'GAME_WIP_LIMIT'):self.admit()
        self.assertEqual(self.highwater(),11);self.assertEqual(self.counts(),[1]*4)
    def test_callback_metadata_alone_cannot_replace_resource_row(self):
        with self.assertRaisesRegex(a.Hold,'RESOURCE_RESERVATION_NOT_BOUND'):
            self.admit(resource_check=lambda *args:dict(scope='DISPOSABLE_RESOURCE_LAB_ONLY',operation_id=self.f.binding['operation_id'],may_dispatch=False,production_go=False,independent_resource_authority_verified=False))
        self.assertEqual(self.counts(),[0]*4)
