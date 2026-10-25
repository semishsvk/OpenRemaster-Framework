import copy,hashlib,unittest
from admission_boundary_base import canonical
from proposal_binding import review,digest
import test_resource_observation as fixture

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.r=fixture.ResourceObservationTests(methodName='test_normal_proposal_still_has_no_authority_or_consumption');self.r.setUp();self.f=self.r.f
        # Synthetic fixture mapped deliberately, not a claim of Studio owner approval.
        self.f.binding['project']='OpenRemasterStudio';self.f.context['project_id']='OpenRemasterStudio'
        import json
        job=json.loads(self.f.job);job['project']='OpenRemasterStudio';self.f.job=canonical(job)
        self.f.binding['job_sha256']=hashlib.sha256(self.f.job).hexdigest();self.f.resign()
        self.f.expected=dict(binding=copy.deepcopy(self.f.binding),shadow_context=copy.deepcopy(self.f.context))
        self.r.inputs=dict(envelope=self.f.envelope,request=self.f.request,grant=self.f.grant,poa_request=self.f.poa_request,job_bytes=self.f.job)
        identity_digest=digest(self.f.call());self.r.expected['work_identity_sha256']=identity_digest;self.r.obs.update(project_id='OpenRemasterStudio',work_identity_sha256=identity_digest)
        self.pins=dict(recipe_sha256='1'*64,toolchain_manifest_sha256='2'*64,dependency_lock_sha256='3'*64)
        b=self.f.binding;c=self.f.context;e=self.r.expected
        self.proposal=dict(schema='OpenRemaster.K003.NamedDevBuildProposal.v1',kind='build_studio_dev',trust_class='DEVELOPMENT',action='submit',operation_id=self.f.request['operation_id'],project='OpenRemasterStudio',recipe='D7.build_studio_dev.v1',adapter='NativeLocalQueue',timeout_seconds=2400,automatic_retries=0,capability='build_studio_dev',source_manifest_sha256=b['source_sha256'],job_bytes_sha256=hashlib.sha256(self.f.job).hexdigest(),request_sha256=digest(self.f.request),owner_fence_sha256=digest(dict(owner_id=b['owner_id'],owner_epoch=b['owner_epoch'],lease_id=b['lease_id'],fence_generation=b['fence_generation'])),resource_fence_sha256=digest(dict(authority_id=e['authority_id'],source_id=e['source_id'],policy_version=c['policy_version'],resource_fence=c['resource_fence'])),**self.pins)
    def call(self):return review(self.proposal,self.r.inputs,self.r.obs,expected_identity=self.f.expected,expected_resource=self.r.expected,recipe_pins=self.pins,owner_keys={'owner-fixture':self.f.owner},envelope_keys={'ed-fixture':self.f.public},now=self.f.now)
    def test_bound_is_still_hold(self):
        result=self.call();self.assertTrue(result['binding_checks_satisfied'],result);self.assertEqual(result['decision'],'HOLD')
        for key in ('independent_authority_verified','observation_consumed','nonce_reserved','broker_called','may_dispatch','may_sign','may_publish','may_promote','may_fallback','production_go'):self.assertIs(result[key],False)
    def test_every_proposal_binding_mismatch(self):
        for key in ('operation_id','source_manifest_sha256','job_bytes_sha256','request_sha256','owner_fence_sha256','resource_fence_sha256'):
            with self.subTest(key=key):
                old=self.proposal[key];self.proposal[key]='f'*len(old);self.assertFalse(self.call()['binding_checks_satisfied']);self.proposal[key]=old
    def test_recipe_changes(self):
        for key in self.pins:
            with self.subTest(key=key):
                old=self.proposal[key];self.proposal[key]='f'*64;self.assertIn('RECIPE_PIN_MISMATCH',self.call()['reason']);self.proposal[key]=old
    def test_missing_recipe_provider(self):
        self.pins=None;self.assertEqual(self.call()['reason'],'INDEPENDENT_RECIPE_PINS_REQUIRED')
    def test_job_bytes_changed(self):
        self.r.inputs['job_bytes']+=b' ';self.assertFalse(self.call()['binding_checks_satisfied'])
    def test_expired_owner_evidence(self):
        self.f.now+=101;self.assertFalse(self.call()['binding_checks_satisfied'])
    def test_forged_owner(self):
        self.f.grant['signature']='0'*64;self.assertFalse(self.call()['binding_checks_satisfied'])
    def test_game_mode(self):
        self.r.obs['telemetry']['game_detected']=True;self.assertIn('GOVERNOR_LIGHT_GAMING',self.call()['reason'])
    def test_fourth_heavy_slot(self):
        self.r.obs['jobs']=[self.r.job(str(i),state='RUNNING') for i in range(3)]+[self.r.job('synthetic-job')];self.assertFalse(self.call()['binding_checks_satisfied'])
    def test_stale_resource(self):
        self.r.obs['valid_until']=self.f.now;self.assertFalse(self.call()['binding_checks_satisfied'])
    def test_status_never_submits(self):
        self.proposal['action']='status';self.assertEqual(self.call()['reason'],'PROPOSAL_SCHEMA')
    def test_repeat_is_not_atomic_admission(self):
        first=self.call();self.assertEqual(first,self.call());self.assertFalse(first['nonce_reserved']);self.assertFalse(first['broker_called'])
    def test_does_not_mutate(self):
        before=copy.deepcopy((self.proposal,self.r.inputs,self.r.obs));self.call();self.assertEqual(before,(self.proposal,self.r.inputs,self.r.obs))
if __name__=='__main__':unittest.main()
