import copy,hashlib,json,unittest
from admission_boundary_base import canonical
from proposal_commitment import DOMAIN,intent_digest,review_committed_proposal
import test_binding as fixture

class CommitmentTests(unittest.TestCase):
    def setUp(self):
        self.b=fixture.BindingTests(methodName='test_bound_is_still_hold');self.b.setUp()
        job=json.loads(self.b.f.job);job['development_intent']=dict(schema=DOMAIN,intent_sha256=intent_digest(self.b.proposal));self.rebind(canonical(job))
    def rebind(self,raw):
        b=self.b;b.f.job=raw;b.f.binding['job_sha256']=hashlib.sha256(raw).hexdigest();b.f.resign()
        b.f.expected=dict(binding=copy.deepcopy(b.f.binding),shadow_context=copy.deepcopy(b.f.context))
        b.r.inputs=dict(envelope=b.f.envelope,request=b.f.request,grant=b.f.grant,poa_request=b.f.poa_request,job_bytes=raw)
        identity_digest=hashlib.sha256(canonical(b.f.call())).hexdigest()
        b.r.expected['work_identity_sha256']=identity_digest;b.r.obs['work_identity_sha256']=identity_digest
        b.proposal['job_bytes_sha256']=hashlib.sha256(raw).hexdigest()
    def call(self):
        b=self.b
        return review_committed_proposal(b.proposal,b.r.inputs,b.r.obs,expected_identity=b.f.expected,expected_resource=b.r.expected,recipe_pins=b.pins,owner_keys={'owner-fixture':b.f.owner},envelope_keys={'ed-fixture':b.f.public},now=b.f.now)
    def test_signed_job_closes_intent_without_recursive_hash(self):
        r=self.call();self.assertTrue(r['commitment_checks_satisfied'],r)
        self.assertEqual(r['evidence']['proposal_sha256'],hashlib.sha256(canonical(self.b.proposal)).hexdigest())
        for key in ('independent_authority_verified','broker_called','nonce_reserved','may_dispatch','may_sign','may_publish','may_promote','may_fallback','production_go'):self.assertIs(r[key],False)
    def test_timeout_change_cannot_reuse_prior_signed_job(self):
        self.b.proposal['timeout_seconds']=1200
        self.assertTrue(self.b.call()['binding_checks_satisfied'])
        self.assertEqual(self.call()['reason'],'SIGNED_JOB_INTENT_MISMATCH')
    def test_caller_repinning_recipe_does_not_change_signed_intent(self):
        self.b.pins['recipe_sha256']='f'*64;self.b.proposal['recipe_sha256']='f'*64
        self.assertTrue(self.b.call()['binding_checks_satisfied'])
        self.assertEqual(self.call()['reason'],'SIGNED_JOB_INTENT_MISMATCH')
    def test_job_mutation_requires_new_owner_signature(self):
        raw=self.b.r.inputs['job_bytes'].replace(b'"intent_sha256":"',b'"intent_sha256":"f')
        self.b.r.inputs['job_bytes']=raw;self.b.proposal['job_bytes_sha256']=hashlib.sha256(raw).hexdigest()
        self.assertFalse(self.call()['commitment_checks_satisfied'])
    def test_missing_commitment_even_with_resigned_job_holds(self):
        job=json.loads(self.b.f.job);del job['development_intent'];self.rebind(canonical(job))
        self.assertEqual(self.call()['reason'],'JOB_INTENT_COMMITMENT_REQUIRED')
    def test_resigned_wrong_commitment_holds(self):
        job=json.loads(self.b.f.job);job['development_intent']['intent_sha256']='0'*64;self.rebind(canonical(job))
        self.assertEqual(self.call()['reason'],'SIGNED_JOB_INTENT_MISMATCH')
    def test_unknown_commitment_version_holds(self):
        job=json.loads(self.b.f.job);job['development_intent']['schema']='unknown';self.rebind(canonical(job))
        self.assertEqual(self.call()['reason'],'JOB_INTENT_COMMITMENT_VERSION')
    def test_self_verified_extra_commitment_claim_holds(self):
        job=json.loads(self.b.f.job);job['development_intent']['verified']=True;self.rebind(canonical(job))
        self.assertEqual(self.call()['reason'],'JOB_INTENT_COMMITMENT_REQUIRED')
    def test_duplicate_job_keys_rejected_even_if_owner_resigns(self):
        raw=self.b.f.job;raw=raw[:-1]+b',"task":"ambiguous"}';self.rebind(raw)
        self.assertEqual(self.call()['reason'],'MALFORMED_OR_UNAVAILABLE_COMMITMENT')
    def test_nonfinite_job_extension_rejected(self):
        raw=self.b.f.job[:-1]+b',"extra":NaN}';self.rebind(raw)
        self.assertEqual(self.call()['reason'],'MALFORMED_OR_UNAVAILABLE_COMMITMENT')
    def test_excluded_job_hash_still_exactly_checked(self):
        self.b.proposal['job_bytes_sha256']='f'*64
        self.assertFalse(self.call()['commitment_checks_satisfied'])
    def test_repeat_does_not_consume_or_authorize(self):
        a=self.call();self.assertEqual(a,self.call());self.assertFalse(a['nonce_reserved'])
    def test_input_detached(self):
        before=copy.deepcopy((self.b.proposal,self.b.r.inputs,self.b.r.obs));self.call();self.assertEqual(before,(self.b.proposal,self.b.r.inputs,self.b.r.obs))
