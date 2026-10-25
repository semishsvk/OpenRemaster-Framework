import copy
import unittest
from glca.core import Hold,digest
from glca.retail import typed_state
from glca.transitions import expand_action_model
from glca.witness import verify_model_witness
from test_transitions import fixture,condition,effect

class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.initial,self.model,self.corpus=fixture()
        expanded=expand_action_model(self.initial,self.model,self.corpus)
        final,path=next(iter(expanded['action_witnesses'].items()))
        self.w=dict(schema='OpenRemaster.RLR.ModelWitness.v1',project='SYNTHETIC',model_digest=digest(self.model),source_manifest_digest=self.corpus['manifest_digest'],initial_state=self.initial['state_digest'],steps=path,final_state=final,ending_id='declared-win')
    def check(self):return verify_model_witness(self.initial,self.model,self.corpus,self.w)
    def rebind(self):self.w['model_digest']=digest(self.model)
    def test_valid_path_has_no_execution_authority(self):
        r=self.check();self.assertEqual(r['steps_checked'],1)
        for key in ('may_dispatch','may_release','may_sign','may_publish','may_promote','may_fallback','native_roundtrip_verified','original_game_validated'):self.assertIs(r[key],False)
    def test_context_tampering(self):
        for key in ('project','model_digest','source_manifest_digest','initial_state','final_state','ending_id'):
            with self.subTest(key=key):
                w=copy.deepcopy(self.w);w[key]='forged'
                with self.assertRaises(Hold):verify_model_witness(self.initial,self.model,self.corpus,w)
    def test_step_tampering(self):
        for key in ('before','after','action_id'):
            with self.subTest(key=key):
                w=copy.deepcopy(self.w);w['steps'][0][key]='forged'
                with self.assertRaises(Hold):verify_model_witness(self.initial,self.model,self.corpus,w)
    def test_prefix_does_not_prove_success(self):
        self.w['steps']=[];self.w['final_state']=self.initial['state_digest']
        with self.assertRaises(Hold):self.check()
    def test_unknown_guard_rejected(self):
        self.model['actions'][0]['guards']=[condition('objects',['missing'],True)];self.rebind()
        with self.assertRaises(Hold):self.check()
    def test_false_guard_rejected(self):
        self.model['actions'][0]['guards']=[condition('globals',['won'],0)];self.rebind()
        with self.assertRaises(Hold):self.check()
    def test_unknown_effect_rejected(self):
        self.model['actions'][0]['effects']=[effect('objects',['missing','open'],True)];self.rebind()
        with self.assertRaises(Hold):self.check()
    def test_unknown_ending_rejected(self):
        self.model['endings'][0]['guards']=[condition('objects',['missing'],True)];self.rebind()
        with self.assertRaises(Hold):self.check()
    def test_action_after_terminal_rejected(self):
        self.w['steps'].append(copy.deepcopy(self.w['steps'][0]))
        with self.assertRaises(Hold):self.check()
    def test_failure_not_success(self):
        self.model['endings'][0]['kind']='FAILURE';self.rebind()
        with self.assertRaises(Hold):self.check()
    def test_extra_authority_field_rejected(self):
        self.w['may_release']=True
        with self.assertRaises(Hold):self.check()
    def test_forged_initial_state_rejected(self):
        self.initial['runtime_verified']=True
        with self.assertRaises(Hold):self.check()
    def test_bound_is_strict(self):
        for bound in (True,0,4097):
            with self.assertRaises(Hold):verify_model_witness(self.initial,self.model,self.corpus,self.w,max_steps=bound)
    def test_input_is_not_mutated(self):
        before=copy.deepcopy((self.initial,self.model,self.corpus,self.w));self.check()
        self.assertEqual(before,(self.initial,self.model,self.corpus,self.w))
    def test_step_limit_rejected_before_replay(self):
        self.w['steps']*=2
        with self.assertRaisesRegex(Hold,'WITNESS_STEP_BOUND'):
            verify_model_witness(self.initial,self.model,self.corpus,self.w,max_steps=1)
    def test_contradictory_endings_rejected(self):
        other=copy.deepcopy(self.model['endings'][0]);other.update(id='loss',kind='FAILURE')
        self.model['endings'].append(other);self.rebind()
        with self.assertRaisesRegex(Hold,'CONTRADICTORY_TERMINAL'):self.check()
    def test_missing_endings_rejected(self):
        self.model['endings']=[];self.rebind()
        with self.assertRaisesRegex(Hold,'SUCCESS_NOT_ESTABLISHED'):self.check()
    def test_extra_step_field_rejected(self):
        self.w['steps'][0]['verified']=True
        with self.assertRaisesRegex(Hold,'STEP_SCHEMA'):self.check()
