import copy
import unittest
from dual_trust_shadow import evaluate,CHECKS,HANDOFF,STATES,ZERO

def fixture():
    handoff={key:'synthetic-reference' for key in HANDOFF}
    handoff.update(commit='a'*40,build_recipe_sha256='b'*64,dependencies_sha256='c'*64)
    return dict(worker=dict(identity='synthetic-production',trust_class='SECURE_PRODUCTION'),
                handoff=handoff,observations={k:True for k in CHECKS},
                fallback_requested=False,**{'from':'CANDIDATE','to':'VERIFIED'})

class ShadowTests(unittest.TestCase):
    def check_safe(self,d,reason):
        result=evaluate(d)
        self.assertIn(reason,result['reasons'])
        self.assertIn(result['decision'],('HOLD','REJECT'))
        for k in ZERO:self.assertIs(result[k],False)
    def test_sixteen_mandatory_negative_cases(self):
        for key in ('identity','credentials','attestation','owner_lease','project_scope',
                    'single_writer','source_integrity','dependencies','fidelity','provenance',
                    'signing_authorization','production_available','no_fallback'):
            with self.subTest(case=key):
                d=fixture();d['observations'][key]=False
                self.check_safe(d,'EVIDENCE_HOLD:'+key)
        d=fixture();d['worker']['trust_class']='DEVELOPMENT'
        self.check_safe(d,'DEVELOPMENT_RELEASE_FORBIDDEN')
        d=fixture();d['worker']['requested_trust_class']='ADMIN'
        self.check_safe(d,'TRUST_ESCALATION_FORBIDDEN')
        d=fixture();d['fallback_requested']=True
        self.check_safe(d,'FALLBACK_FORBIDDEN_OR_UNKNOWN')
    def test_every_transition_pair(self):
        for a in STATES:
            for b in STATES:
                with self.subTest(before=a,after=b):
                    d=fixture();d.update({'from':a,'to':b})
                    if STATES.index(b)!=STATES.index(a)+1:self.check_safe(d,'INVALID_STATE_TRANSITION')
                    else:self.check_safe(d,'INDEPENDENT_AUTHORITY_ADAPTERS_NOT_CONNECTED')
    def test_self_attestation_never_authorizes(self):
        self.check_safe(fixture(),'INDEPENDENT_AUTHORITY_ADAPTERS_NOT_CONNECTED')
    def test_unsigned_publish(self):
        d=fixture();d.update({'from':'SIGNED','to':'PUBLISHED'})
        self.check_safe(d,'UNSIGNED_PUBLICATION_FORBIDDEN')
    def test_missing_handoff_fields(self):
        for key in HANDOFF:
            d=fixture();del d['handoff'][key]
            self.check_safe(d,'HANDOFF_MISSING:'+key)
    def test_unknown_stale_wrong_type_evidence(self):
        for value in (None,'true',1,[],{},False):
            d=fixture();d['observations']['owner_lease']=value
            self.check_safe(d,'EVIDENCE_HOLD:owner_lease')
    def test_malformed_documents(self):
        for value in (None,[],1,{},dict(worker=[],handoff=[],observations=[])):
            self.assertIn(evaluate(value)['decision'],('HOLD','REJECT'))
    def test_no_input_mutation(self):
        d=fixture();before=copy.deepcopy(d);evaluate(d);self.assertEqual(d,before)
    def test_digest_alone_never_enough(self):
        self.check_safe({'sha256':'a'*64},'INDEPENDENT_AUTHORITY_ADAPTERS_NOT_CONNECTED')
    def test_unknown_worker(self):
        d=fixture();d['worker']={};self.check_safe(d,'IDENTITY_MISSING')
    def test_mutable_revision(self):
        d=fixture();d['handoff']['commit']='main';self.check_safe(d,'IMMUTABLE_COMMIT_REQUIRED')

if __name__=='__main__':unittest.main(verbosity=2)
