import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from rejection_evidence import rejection_record,export_bundle,validate_record,digest
import test_resource_transaction as fixture
import resource_authority as authority

RECORDS=[]
class RejectionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.context=dict(attempt_id='a'*32,operation_id='b'*32,input_digests=dict(job_sha256='c'*64,request_sha256='d'*64,proposal_sha256=None))
    def record(self,decision='HOLD',reason='STALE_OWNER_LEASE'):return rejection_record(dict(decision=decision,reason=reason),self.context,observed_at=1800000000)
    def test_known_reason_has_integrity_without_authority(self):
        r=self.record();self.assertEqual(validate_record(r),r);self.assertEqual(r['transaction_outcome'],'NOT_ATTESTED')
        for key in ('independent_authority_verified','durability_verified','may_dispatch','may_sign','may_publish','may_promote','may_fallback','production_go'):self.assertIs(r[key],False)
    def test_unknown_reason_does_not_export_raw_paths_or_secrets(self):
        r=self.record(reason='secret-token C:/private/identity.key');self.assertEqual(r['reason_code'],'UNCLASSIFIED_FAILURE');self.assertNotIn('secret-token',json.dumps(r))
    def test_accepted_decision_never_exports_as_release_evidence(self):
        for value in ('PASS','ACCEPTED','SIGNED','PUBLISHED',True,None):
            with self.subTest(value=value),self.assertRaises(ValueError):self.record(decision=value)
    def test_extra_fields_cannot_smuggle_credentials(self):
        with self.assertRaises(ValueError):rejection_record(dict(decision='HOLD',reason='STALE_OWNER_LEASE',credentials='secret'),self.context,observed_at=1)
    def test_missing_and_unknown_identity_still_recordable(self):
        self.context['operation_id']=None;self.context['input_digests']={k:None for k in self.context['input_digests']};self.assertIsNone(self.record(reason='UNKNOWN_WORKER_IDENTITY')['operation_id'])
    def test_tampered_record_and_permission_claims_rejected(self):
        for key,value in [('reason_code','INVALID_CREDENTIALS'),('may_dispatch',True),('durability_verified',True),('independent_authority_verified',True),('record_sha256','f'*64)]:
            with self.subTest(key=key),self.assertRaises(ValueError):validate_record(dict(self.record(),**{key:value}))
    def test_recomputed_digest_does_not_override_disabled_permissions(self):
        r=self.record();r['may_sign']=True;r['record_sha256']=digest({k:v for k,v in r.items() if k!='record_sha256'})
        with self.assertRaises(ValueError):validate_record(r)
    def test_duplicate_attempts_rejected_but_retries_are_distinct(self):
        r=self.record()
        with self.assertRaises(ValueError):export_bundle([r,r])
        self.context['attempt_id']='e'*32;self.assertEqual(export_bundle([r,self.record()])['record_count'],2)
    def test_bounded_export_and_empty_rejected(self):
        for records in ([],[self.record()]*129,None):
            with self.assertRaises(ValueError):export_bundle(records)
    def test_time_and_hash_types_strict(self):
        for value in (True,-1,float('nan'),'now'):
            with self.assertRaises(ValueError):rejection_record(dict(decision='HOLD',reason='STALE_OWNER_LEASE'),self.context,observed_at=value)
        self.context['input_digests']['job_sha256']=True
        with self.assertRaises(ValueError):self.record()
    def test_detached_and_json_roundtrip(self):
        r=self.record();bundle=export_bundle([r]);bundle['records'][0]['reason_code']='changed';self.assertEqual(r['reason_code'],'STALE_OWNER_LEASE');self.assertEqual(validate_record(json.loads(json.dumps(r))),r)
    def test_export_write_failure_does_not_authorize(self):
        bundle=export_bundle([self.record()])
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(OSError):Path(temp).write_text(json.dumps(bundle),encoding='utf-8')
        self.assertFalse(bundle['may_dispatch']);self.assertFalse(bundle['durability_verified'])

class ActualRollbackEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.t=fixture.ResourceTransactionTests(methodName='test_atomic_ack_binds_resource_and_reopens');self.t.setUp();self.addCleanup(self.t.doCleanups)
    def capture(self,index,action):
        try:action()
        except authority.Hold as e:
            t=self.t
            context=dict(attempt_id=f'{index:032x}',operation_id=t.f.binding['operation_id'],input_digests=dict(job_sha256=hashlib.sha256(t.f.job).hexdigest(),request_sha256=digest(t.f.request),proposal_sha256=None))
            r=rejection_record(dict(decision='HOLD',reason=str(e)),context,observed_at=t.f.now);RECORDS.append(r);return r
        self.fail('EXPECTED_HOLD_NOT_RAISED')
    def test_owner_rejection_exports_after_rollback(self):
        with self.t.store.connect() as db:db.execute("UPDATE owners SET status='RELEASED'")
        r=self.capture(1,self.t.admit);self.assertEqual(r['reason_code'],'OWNER_EPOCH_GENERATION_LEASE_OR_SOURCE_HOLD');self.assertEqual(self.t.counts(),[0]*4);self.assertEqual(self.t.highwater(),10)
    def test_resource_fence_rejection_exports_after_rollback(self):
        with self.t.store.connect() as db:db.execute('UPDATE resource_state SET fence=4')
        r=self.capture(2,self.t.admit);self.assertEqual(r['reason_code'],'RESOURCE_FENCE_OR_POLICY_CHANGED');self.assertEqual(self.t.counts(),[0]*4)
    def test_replay_exports_without_another_admission(self):
        self.t.admit();r=self.capture(3,self.t.admit);self.assertEqual(r['reason_code'],'RESOURCE_OPERATION_ALREADY_PRESENT_QUERY_ONLY');self.assertEqual(self.t.counts(),[1]*4);self.t.store.audit()
    def test_game_hold_exports_without_resource_consumption(self):
        self.t.case.obs['telemetry']['game_detected']=True
        r=self.capture(4,self.t.admit);self.assertEqual(r['reason_code'],'RESOURCE_REVIEW_GOVERNOR_LIGHT_GAMING');self.assertEqual(self.t.counts(),[0]*4);self.assertEqual(self.t.highwater(),10)
