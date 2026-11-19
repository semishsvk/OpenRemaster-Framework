import base64,copy,hashlib,secrets,unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import authority as poa
from admission_boundary_base import canonical
from work_identity import review_work_identity

def seal(body,key):
    import hmac
    body=dict(body,key_id='owner-fixture');body['signature']=hmac.new(key,poa.canonical(body),hashlib.sha256).hexdigest();return body

class WorkIdentityTests(unittest.TestCase):
    def setUp(self):
        self.owner=secrets.token_bytes(32);self.ed=Ed25519PrivateKey.generate();self.public=self.ed.public_key().public_bytes_raw();self.now=1800000000
        self.job=canonical(dict(schema='ORCH-K003.Job.v1',job_id='synthetic-job',project='SYNTHETIC',task='test-only'))
        self.binding=dict(project='SYNTHETIC',edition='SYNTHETIC_EDITION',scenario='build_studio_dev',source_sha256='a'*64,job_id='synthetic-job',job_sha256=hashlib.sha256(self.job).hexdigest(),snapshot_sha256='b'*64,checkpoint_sha256='c'*64,operation_id='d'*32,nonce='synthetic_nonce_0123456789',owner_epoch=1,fence_generation=7,policy_epoch=2,owner_id='synthetic-owner',lease_id='synthetic-lease',heavy=True)
        self.context=dict(operation_id=self.binding['operation_id'],project_id='SYNTHETIC',capability='build_studio_dev',fence=7,lease_id='synthetic-lease',resource_fence=3,authority_id='synthetic-authority',policy_version='synthetic-policy',trust_class='DEVELOPMENT')
        self.request=dict(action='submit',operation_id=self.binding['operation_id'],scenario='build_studio_dev')
        self.resign()
        self.expected=dict(binding=copy.deepcopy(self.binding),shadow_context=copy.deepcopy(self.context))
    def resign(self):
        body=dict(self.binding,schema=poa.GRANT_SCHEMA,audience=poa.AUDIENCE,purpose=poa.GRANT_PURPOSE,mode='V2_REQUIRED',issued_at_unix=self.now-1,expires_at_unix=self.now+100)
        self.grant=seal(body,self.owner);self.poa_request=dict(self.binding,schema=poa.REQUEST_SCHEMA,protocol='V2_REQUIRED')
        b=dict(schema='OpenRemaster.ExecutionAdmission.v1',operation_id=self.binding['operation_id'],project_id=self.binding['project'],capability=self.binding['scenario'],fence=self.binding['fence_generation'],request_sha256=hashlib.sha256(canonical(self.request)).hexdigest(),nonce=self.binding['nonce'],issuer_kid='ed-fixture',not_after=self.now+100)
        b['signature_b64']=base64.b64encode(self.ed.sign(canonical(b))).decode();self.envelope=b
    def call(self,**kw):
        args=dict(expected=self.expected,owner_keys={'owner-fixture':self.owner},envelope_keys={'ed-fixture':self.public},now=self.now);args.update(kw)
        return review_work_identity(self.envelope,self.request,self.grant,self.poa_request,self.job,**args)
    def test_all_bindings_preserved_but_no_resource_authority(self):
        r=self.call();self.assertTrue(r['identity_checks_satisfied']);self.assertEqual(r['bindings'],self.binding);self.assertEqual(r['reason'],'RESOURCE_AUTHORITY_UNAVAILABLE');self.assertEqual(r['decision'],'HOLD')
        for k in ('dispatch_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','nonce_reserved','resource_authority_verified','production_go'):self.assertIs(r[k],False)
    def test_every_expected_binding_is_mandatory(self):
        for key in poa.BIND:
            expected=copy.deepcopy(self.expected);del expected['binding'][key]
            self.assertEqual(self.call(expected=expected)['reason'],'EXPECTED_BINDING_INCOMPLETE',key)
    def test_every_resigned_changed_binding_rejects_against_expected(self):
        for key,value in [('source_sha256','f'*64),('snapshot_sha256','f'*64),('checkpoint_sha256','f'*64),('owner_epoch',2),('policy_epoch',3),('edition','OTHER'),('owner_id','OTHER'),('heavy',False),('job_id','other-job'),('lease_id','other-lease'),('operation_id','e'*32),('project','FOREIGN'),('scenario','publish.production'),('nonce','other_nonce_0123456789')]:
            old=copy.deepcopy(self.binding);self.binding[key]=value;self.resign()
            self.assertEqual(self.call()['decision'],'REJECT',key)
            self.binding=old;self.resign()
    def test_python_boolean_integer_request_coercion_rejected(self):
        self.poa_request['owner_epoch']=True
        scope,_=poa.verify_grant(self.grant,{'owner-fixture':self.owner},self.now)
        # Reproduce the existing equality-based check; do not claim the original is fixed.
        self.assertEqual(len(poa.verify_request(self.grant,self.poa_request,self.job,scope)),64)
        self.assertEqual(self.call()['reason'],'REQUEST_BINDING_TYPE_MISMATCH')
    def test_mutated_job_bytes_rejected(self):
        self.job+=b' ';self.assertEqual(self.call()['reason'],'POAV2_JOB_BYTES_SHA_MISMATCH')
    def test_invalid_owner_signature_rejected(self):
        self.grant['signature']='0'*64;self.assertEqual(self.call()['reason'],'POAV2_SIGNATURE_INVALID')
    def test_invalid_ed_signature_rejected(self):
        self.envelope['signature_b64']=base64.b64encode(b'x'*64).decode();self.assertEqual(self.call()['reason'],'SHADOW_SIGNATURE')
    def test_alias_scenario_not_automatically_renamed(self):
        self.binding['scenario']='isolated';self.resign();self.expected['binding']['scenario']='isolated'
        self.assertEqual(self.call()['reason'],'CROSSWALK_MISMATCH_CAPABILITY')
    def test_nonce_must_bind_both_envelopes(self):
        self.envelope['nonce']='substitute';self.assertEqual(self.call()['reason'],'NONCE_CROSSWALK_MISMATCH')
    def test_resource_fence_not_inferred_from_owner_fence(self):
        del self.expected['shadow_context']['resource_fence'];self.assertEqual(self.call()['reason'],'EXPECTED_CONTEXT_INCOMPLETE')
    def test_resource_data_does_not_create_an_authority(self):
        self.assertEqual(self.call()['reason'],'RESOURCE_AUTHORITY_UNAVAILABLE')
        self.expected['shadow_context']['resource_fence']=1000;self.assertEqual(self.call()['reason'],'RESOURCE_AUTHORITY_UNAVAILABLE')
    def test_shadow_project_operation_and_fence_must_match_exactly(self):
        for key,value in [('project_id','FOREIGN'),('operation_id','e'*32),('fence',8),('lease_id','foreign')]:
            e=copy.deepcopy(self.expected);e['shadow_context'][key]=value
            self.assertEqual(self.call(expected=e)['decision'],'REJECT',key)
    def test_shared_key_material_rejected(self):
        self.assertEqual(self.call(owner_keys={'owner-fixture':self.public})['reason'],'SIGNING_DOMAIN_KEY_MATERIAL_OVERLAP')
    def test_trust_class_cannot_escalate(self):
        self.expected['shadow_context']['trust_class']='SECURE_PRODUCTION';self.assertEqual(self.call()['decision'],'REJECT')
    def test_expired_or_unverified_clock_holds_or_rejects(self):
        self.assertEqual(self.call(now=self.now+100)['decision'],'REJECT')
        for clock in (None,True,float('nan'),-1):self.assertEqual(self.call(now=clock)['reason'],'VERIFIED_CLOCK_REQUIRED')
    def test_missing_key_registry_holds(self):
        self.assertEqual(self.call(owner_keys=None)['reason'],'PINNED_KEY_REGISTRIES_REQUIRED')
    def test_output_not_mutating_input(self):
        before=copy.deepcopy((self.expected,self.grant,self.envelope,self.poa_request));r=self.call();r['bindings']['owner_id']='changed'
        self.assertEqual(before,(self.expected,self.grant,self.envelope,self.poa_request))
    def test_precomputed_claim_cannot_replace_signed_input(self):
        self.grant={'status':'VERIFIED'};self.assertEqual(self.call()['decision'],'REJECT')
