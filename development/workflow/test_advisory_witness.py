import copy,unittest
from glca.core import Hold,digest
from glca.transitions import expand_action_model
from master_workflow import advisory_package
from glca.retail import FIELDS,typed_state

def fixture():
    files=[dict(path='fixture.dat',bytes=64,sha256='a'*64)]
    corpus=dict(schema='OpenRemaster.RLR.CorpusManifest.v1',project='SYNTHETIC',files=files,manifest_digest=digest(['SYNTHETIC',files]))
    ref=dict(path='fixture.dat',sha256='a'*64,offset=0,length=8)
    model=dict(schema='OpenRemaster.RLR.ActionModel.v1',project='SYNTHETIC',source_manifest_digest=corpus['manifest_digest'],actions=[dict(id='finish',guards=[],effects=[dict(op='set',field='globals',path=['won'],value=True)],source_refs=[ref])],endings=[dict(id='declared-win',kind='SUCCESS',guards=[dict(field='globals',path=['won'],equals=True)],source_refs=[ref])])
    fields={k:{'known':True,'value':{}} for k in FIELDS};fields['globals']['value']={'won':False}
    return typed_state('SYNTHETIC',fields),model,corpus

class AdvisoryWitnessTests(unittest.TestCase):
    def setUp(self):
        initial,model,corpus=fixture();r=expand_action_model(initial,model,corpus)
        final,path=next(iter(r['action_witnesses'].items()))
        witness=dict(schema='OpenRemaster.RLR.ModelWitness.v1',project='SYNTHETIC',model_digest=digest(model),source_manifest_digest=corpus['manifest_digest'],initial_state=initial['state_digest'],steps=path,final_state=final,ending_id='declared-win')
        self.bundle=dict(initial=initial,model=model,corpus=corpus,witness=witness)
    def call(self,**kw):return advisory_package('SYNTHETIC',[],[],['script'],'a'*64,**kw)
    def test_checked_path_bound_without_authority(self):
        r=self.call(model_witness=self.bundle);o=r['model_witness_observation']
        self.assertEqual(o['witness_digest'],digest(self.bundle['witness']))
        self.assertEqual(o['project'],'SYNTHETIC');self.assertEqual(o['source_manifest_digest'],self.bundle['corpus']['manifest_digest'])
        self.assertEqual(r['status'],'HOLD_ADMISSION_REQUIRED')
        for field in ('may_dispatch','may_sign','may_publish','production_go'):self.assertIs(r[field],False)
        self.assertEqual(r['resource_request']['heavy_slots'],0)
    def test_legacy_digest_and_shape_preserved(self):
        r=self.call();self.assertNotIn('model_witness_observation',r)
        self.assertEqual(r['proposal_digest'],digest(['SYNTHETIC',[],[],['script'],'a'*64,'UNKNOWN']))
        self.assertEqual(r,self.call(model_witness=None))
    def test_bare_verification_result_rejected(self):
        with self.assertRaises(Hold):self.call(model_witness=dict(status='STATIC_CANDIDATE',may_release=False))
    def test_forged_path_rejected_not_observed(self):
        self.bundle['witness']['steps'][0]['after']='0'*64
        with self.assertRaises(Hold):self.call(model_witness=self.bundle)
    def test_foreign_project_in_each_input_rejected(self):
        for key in self.bundle:
            with self.subTest(key=key):
                b=copy.deepcopy(self.bundle);b[key]['project']='FOREIGN'
                with self.assertRaisesRegex(Hold,'ADVISORY_WITNESS_PROJECT'):self.call(model_witness=b)
    def test_source_mismatch_rejected(self):
        self.bundle['corpus']['files'][0]['sha256']='b'*64
        with self.assertRaises(Hold):self.call(model_witness=self.bundle)
    def test_model_mismatch_rejected(self):
        self.bundle['model']['actions'][0]['effects'][0]['value']=False
        with self.assertRaises(Hold):self.call(model_witness=self.bundle)
    def test_extra_claim_rejected(self):
        self.bundle['verified']=True
        with self.assertRaises(Hold):self.call(model_witness=self.bundle)
    def test_all_governor_modes_keep_admission_hold(self):
        for mode in ('NORMAL','GAME','GAMING','LIGHT','UNKNOWN'):
            r=self.call(model_witness=self.bundle,governor_mode=mode)
            self.assertFalse(r['may_dispatch']);self.assertEqual(r['resource_request']['heavy_slots'],0)
    def test_valid_model_change_invalidates_plan_identity(self):
        old=self.call(model_witness=self.bundle)
        self.bundle['model']['actions'][0]['source_refs'][0]['offset']=1
        self.bundle['witness']['model_digest']=digest(self.bundle['model'])
        self.assertNotEqual(old['proposal_digest'],self.call(model_witness=self.bundle)['proposal_digest'])
    def test_inputs_not_mutated(self):
        before=copy.deepcopy(self.bundle);self.call(model_witness=self.bundle);self.assertEqual(before,self.bundle)
    def test_unknown_endings_cannot_enter_plan(self):
        self.bundle['model']['endings'][0]['guards'][0]['path']=['unknown']
        self.bundle['witness']['model_digest']=digest(self.bundle['model'])
        with self.assertRaises(Hold):self.call(model_witness=self.bundle)
