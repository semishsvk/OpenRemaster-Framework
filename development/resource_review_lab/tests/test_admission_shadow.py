import base64,copy,hashlib,threading,unittest
from concurrent.futures import ThreadPoolExecutor
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from admission_boundary_base import canonical
from admission_shadow import evaluate_shadow_admission

class SyntheticAuthority:
    """In-memory test double only; no production durability or authentication."""
    def __init__(self,expected):self.expected=copy.deepcopy(expected);self.used=set();self.lock=threading.Lock();self.calls=0
    def __call__(self,claim):
        with self.lock:
            self.calls+=1;status='RESERVED';nonce=(claim['issuer_kid'],claim['nonce'])
            if claim['lease_id']!=self.expected['lease_id']:status='STALE_LEASE'
            elif any(claim[k]!=self.expected[k] for k in ('fence','resource_fence')):status='STALE_FENCE'
            elif any(claim[k]!=self.expected[k] for k in ('project_id','capability','operation_id','policy_version','trust_class')):status='SCOPE_DENIED'
            elif claim['not_after']<=100:status='EXPIRED'
            elif nonce in self.used:status='REPLAY'
            if status=='RESERVED':self.used.add(nonce)
            return dict(schema='OpenRemaster.ShadowNonceReceipt.v1',status=status,authority_id=self.expected['authority_id'],claim_sha256=hashlib.sha256(canonical(claim)).hexdigest(),receipt_id='synthetic-receipt',event_sequence=self.calls)

class ShadowAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate();self.keys={'synthetic-key':self.key.public_key().public_bytes_raw()}
        self.expected=dict(operation_id='a'*32,project_id='SYNTHETIC',capability='build_studio_dev',fence=7,resource_fence=3,lease_id='synthetic-lease',authority_id='synthetic-authority',policy_version='synthetic-policy-v1',trust_class='DEVELOPMENT')
        self.request=dict(action='submit',operation_id='a'*32,scenario='build_studio_dev')
        self.body=dict(schema='OpenRemaster.ExecutionAdmission.v1',operation_id='a'*32,project_id='SYNTHETIC',capability='build_studio_dev',fence=7,request_sha256=hashlib.sha256(canonical(self.request)).hexdigest(),nonce='synthetic-nonce',issuer_kid='synthetic-key',not_after=200.0)
        self.authority=SyntheticAuthority(self.expected)
    def envelope(self,**changes):
        b=dict(self.body,**changes);b['signature_b64']=base64.b64encode(self.key.sign(canonical(b))).decode();return b
    def call(self,**kw):
        args=dict(expected=self.expected,authority=self.authority,now=100.0);args.update(kw)
        return evaluate_shadow_admission(self.envelope(),self.request,self.keys,**args)
    def test_valid_is_shadow_hold_with_every_capability_disabled(self):
        r=self.call();self.assertTrue(r['checks_satisfied']);self.assertEqual(r['decision'],'HOLD')
        for k in ('dispatch_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go','independent_authority_verified'):self.assertIs(r[k],False)
    def test_missing_context_holds_before_authority(self):
        self.assertEqual(self.call(expected=None)['reason'],'EXPECTED_CONTEXT_REQUIRED');self.assertEqual(self.authority.calls,0)
    def test_all_context_mismatches_rejected_before_reservation(self):
        for key,value in [('operation_id','b'*32),('project_id','FOREIGN'),('capability','publish.production'),('project_id',None),('capability',None),('fence',1)]:
            r=evaluate_shadow_admission(self.envelope(**{key:value}),self.request,self.keys,expected=self.expected,authority=self.authority,now=100)
            self.assertEqual(r['decision'],'REJECT',(key,r));self.assertFalse(r['checks_satisfied'])
        self.assertEqual(self.authority.calls,0)
    def test_unknown_key_rejected(self):
        r=evaluate_shadow_admission(self.envelope(),self.request,{},expected=self.expected,authority=self.authority,now=100)
        self.assertEqual(r['reason'],'ISSUER_NOT_TRUSTED');self.assertEqual(self.authority.calls,0)
    def test_expiry_rejected_at_boundary(self):
        self.assertEqual(self.call(now=200)['reason'],'EXPIRED');self.assertEqual(self.authority.calls,0)
    def test_request_tampering_rejected(self):
        self.request['operation_id']='b'*32;self.assertEqual(self.call()['decision'],'REJECT')
    def test_digest_tampering_rejected(self):
        self.body['request_sha256']='0'*64;self.assertEqual(self.call()['reason'],'REQUEST_DIGEST_MISMATCH')
    def test_invalid_signature_rejected_without_nonce_consumption(self):
        e=self.envelope();e['signature_b64']=base64.b64encode(b'x'*64).decode()
        r=evaluate_shadow_admission(e,self.request,self.keys,expected=self.expected,authority=self.authority,now=100)
        self.assertEqual(r['reason'],'SIGNATURE');self.assertEqual(self.authority.calls,0)
    def test_replay_rejected_by_atomic_test_double(self):
        self.assertTrue(self.call()['checks_satisfied']);self.assertEqual(self.call()['reason'],'AUTHORITY_REPLAY')
    def test_concurrent_nonce_has_exactly_one_reservation(self):
        with ThreadPoolExecutor(max_workers=16) as pool:results=list(pool.map(lambda _:self.call(),range(32)))
        self.assertEqual(sum(r['checks_satisfied'] for r in results),1)
        self.assertEqual(sum(r['reason']=='AUTHORITY_REPLAY' for r in results),31)
        self.assertTrue(all(not r['dispatch_authorized'] for r in results))
    def test_lease_changed_after_context_snapshot(self):
        self.authority.expected['lease_id']='new-lease';self.assertEqual(self.call()['reason'],'AUTHORITY_STALE_LEASE')
    def test_fences_changed_after_context_snapshot(self):
        for key in ('fence','resource_fence'):
            self.authority=SyntheticAuthority(self.expected);self.authority.expected[key]+=1
            self.assertEqual(self.call()['reason'],'AUTHORITY_STALE_FENCE')
    def test_policy_changed_after_snapshot(self):
        self.authority.expected['policy_version']='new-policy';self.assertEqual(self.call()['reason'],'AUTHORITY_SCOPE_DENIED')
    def test_unavailable_authority_holds(self):
        self.assertEqual(self.call(authority=None)['reason'],'AUTHORITY_UNAVAILABLE')
    def test_authority_failure_is_uncertain_and_never_retried(self):
        calls=[]
        def fail(claim):calls.append(claim);raise RuntimeError('synthetic')
        r=self.call(authority=fail);self.assertEqual(r['reason'],'AUTHORITY_RESULT_UNCERTAIN');self.assertEqual(len(calls),1)
        self.assertFalse(r['automatic_retry'])
    def test_receipt_context_cannot_be_rebound(self):
        for key,value in [('claim_sha256','0'*64),('authority_id','foreign'),('event_sequence',True),('receipt_id','')]:
            self.authority=SyntheticAuthority(self.expected)
            def bad(claim):return dict(self.authority(claim),**{key:value})
            self.assertEqual(self.call(authority=bad)['reason'],'AUTHORITY_RECEIPT_MISMATCH')
    def test_authority_cannot_mutate_local_claim(self):
        def mutate(claim):claim['nonce']='substitute';return self.authority(claim)
        self.assertEqual(self.call(authority=mutate)['reason'],'AUTHORITY_RECEIPT_MISMATCH')
    def test_missing_or_unknown_receipt_is_hold(self):
        for value in (None,{},dict(status='RESERVED')):
            self.assertEqual(self.call(authority=lambda claim:value)['reason'],'AUTHORITY_RECEIPT_SCHEMA')
    def test_production_class_never_inherits_development_path(self):
        self.expected['trust_class']='SECURE_PRODUCTION';self.assertEqual(self.call()['reason'],'DEVELOPMENT_SCOPE_ONLY')
    def test_development_context_cannot_authorize_publication(self):
        self.expected['capability']='publish.production';self.request['scenario']='publish.production'
        self.assertEqual(self.call()['reason'],'CAPABILITY_OUTSIDE_CAPTURED_DEV_SCOPE');self.assertEqual(self.authority.calls,0)
    def test_unverified_clock_holds(self):
        for clock in (None,True,-1,float('nan'),float('inf'),10**500):
            self.assertEqual(self.call(now=clock)['reason'],'VERIFIED_CLOCK_REQUIRED')
    def test_invalid_fence_context_holds(self):
        for value in (True,0,-1,'7'):
            self.expected['fence']=value;self.assertEqual(self.call()['reason'],'EXPECTED_FENCE_INVALID')
    def test_schema_and_bounds_fail_closed(self):
        e=self.envelope();e['extra']=True
        r=evaluate_shadow_admission(e,self.request,self.keys,expected=self.expected,authority=self.authority,now=100)
        self.assertEqual(r['reason'],'ENVELOPE_SCHEMA')
        e={'oversized':'x'*17000}
        r=evaluate_shadow_admission(e,self.request,self.keys,expected=self.expected,authority=self.authority,now=100)
        self.assertEqual(r['reason'],'ENVELOPE_SIZE')
    def test_inputs_unchanged_and_audit_contains_only_digests(self):
        before=copy.deepcopy((self.expected,self.request,self.body));r=self.call()
        self.assertEqual(before,(self.expected,self.request,self.body));self.assertTrue(r['evidence'])
        self.assertTrue(all(len(value)==64 for value in r['evidence'].values()))

if __name__=='__main__':unittest.main()
