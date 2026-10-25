"""Synthetic action-model contract tests; no actual game corpus or runtime."""
import copy
import unittest
from glca.core import Hold,digest
from glca.retail import FIELDS,typed_state
from glca.transitions import expand_action_model,validate_action_model,action_model_atlas

def condition(field,path,value):return dict(field=field,path=path,equals=value)
def effect(field,path,value):return dict(op='set',field=field,path=path,value=value)
def fixture():
    files=[dict(path='synthetic.dat',bytes=64,sha256='a'*64)]
    corpus=dict(schema='OpenRemaster.RLR.CorpusManifest.v1',project='SYNTHETIC',files=files,manifest_digest=digest(['SYNTHETIC',files]))
    ref=dict(path='synthetic.dat',sha256='a'*64,offset=0,length=8)
    model=dict(schema='OpenRemaster.RLR.ActionModel.v1',project='SYNTHETIC',source_manifest_digest=corpus['manifest_digest'],actions=[dict(id='unlock',guards=[condition('globals',['won'],False)],effects=[effect('globals',['won'],True)],source_refs=[ref])],endings=[dict(id='declared-win',kind='SUCCESS',guards=[condition('globals',['won'],True)],source_refs=[ref])])
    fields={k:{'known':True,'value':{}} for k in FIELDS};fields['globals']['value']={'won':False}
    return typed_state('SYNTHETIC',fields),model,corpus

class TransitionTests(unittest.TestCase):
    def test_source_bound_path_reuses_solver_and_keeps_model_scope(self):
        initial,model,corpus=fixture();r=expand_action_model(initial,model,corpus)
        self.assertEqual(len(r['states']),2);self.assertEqual(len(r['success_candidates']),1)
        path=next(iter(r['action_witnesses'].values()));self.assertEqual([s['action_id'] for s in path],['unlock'])
        self.assertFalse(r['original_game_validated']);self.assertFalse(r['native_roundtrip_verified'])
        self.assertFalse(r['may_dispatch']);self.assertFalse(r['may_release']);self.assertEqual(r['confirmed_softlocks'],0)
    def test_unknown_guard_never_enables_action(self):
        initial,model,corpus=fixture();initial['fields']['inventory']={'known':False};initial=typed_state('SYNTHETIC',initial['fields'])
        model['actions'][0]['guards']=[condition('inventory',['key'],'actor')]
        r=expand_action_model(initial,model,corpus)
        self.assertEqual(r['transitions'],[]);self.assertEqual(r['action_witnesses'],{})
        self.assertTrue(any(x['reason']=='ACTION_GUARD_UNKNOWN' for x in r['unknowns']))
    def test_false_guard_overrides_unknown_in_conjunction(self):
        initial,model,corpus=fixture();model['actions'][0]['guards']=[condition('inventory',['unknown'],True),condition('globals',['won'],True)]
        r=expand_action_model(initial,model,corpus);self.assertEqual(r['transitions'],[])
        self.assertFalse(any(x['reason']=='ACTION_GUARD_UNKNOWN' for x in r['unknowns']))
    def test_boolean_integer_guard_distinction(self):
        initial,model,corpus=fixture();model['actions'][0]['guards']=[condition('globals',['won'],0)]
        self.assertEqual(expand_action_model(initial,model,corpus)['transitions'],[])
    def test_missing_nested_effect_target_stays_unknown(self):
        initial,model,corpus=fixture();model['actions'][0]['effects']=[effect('objects',['missing','open'],True)]
        r=expand_action_model(initial,model,corpus);self.assertEqual(len(r['states']),1)
        self.assertEqual(r['unknowns'][0]['reason'],'EFFECT_TARGET_UNKNOWN')
    def test_unknown_ending_blocks_certain_completion_claim(self):
        initial,model,corpus=fixture();model['endings'][0]['guards']=[condition('terminal',['won'],True)]
        r=expand_action_model(initial,model,corpus);self.assertEqual(r['success_candidates'],{});self.assertEqual(r['transitions'],[])
    def test_unknown_conflicting_terminal_never_becomes_success(self):
        initial,model,corpus=fixture();model['endings'][0]['guards']=[condition('globals',['won'],False)]
        extra=copy.deepcopy(model['endings'][0]);extra.update(id='maybe-dead',kind='FAILURE',guards=[condition('terminal',['dead'],True)]);model['endings'].append(extra)
        self.assertEqual(expand_action_model(initial,model,corpus)['success_candidates'],{})
    def test_conflicting_known_terminal_predicates_rejected(self):
        initial,model,corpus=fixture();model['endings'][0]['guards']=[condition('globals',['won'],False)]
        extra=copy.deepcopy(model['endings'][0]);extra.update(id='also-dead',kind='FAILURE');model['endings'].append(extra)
        with self.assertRaisesRegex(Hold,'CONTRADICTORY_TERMINAL'):expand_action_model(initial,model,corpus)
    def test_source_identity_and_ranges_rejected(self):
        for case in ('project','manifest','file_hash','offset','duplicate_file'):
            initial,model,corpus=fixture()
            if case=='project':model['project']='FOREIGN'
            if case=='manifest':model['source_manifest_digest']='b'*64
            if case=='file_hash':model['actions'][0]['source_refs'][0]['sha256']='b'*64
            if case=='offset':model['actions'][0]['source_refs'][0]['offset']=64
            if case=='duplicate_file':corpus['files'].append(copy.deepcopy(corpus['files'][0]))
            with self.subTest(case=case):
                with self.assertRaises(Hold):expand_action_model(initial,model,corpus)
    def test_duplicate_actions_and_overlapping_effects_rejected(self):
        initial,model,corpus=fixture();model['actions'].append(copy.deepcopy(model['actions'][0]))
        with self.assertRaises(Hold):expand_action_model(initial,model,corpus)
        initial,model,corpus=fixture();model['actions'][0]['effects'].append(effect('globals',[],{}))
        with self.assertRaisesRegex(Hold,'CONFLICTING_EFFECT'):expand_action_model(initial,model,corpus)
    def test_owner_and_timer_distinctions_survive_deduplication(self):
        initial,model,corpus=fixture();base=copy.deepcopy(model['actions'][0]);model['actions']=[];model['endings']=[]
        for name,owner,timer in [('a','actor-a',1),('b','actor-b',1),('c','actor-a',2)]:
            row=copy.deepcopy(base);row.update(id=name,guards=[],effects=[effect('inventory',['key'],owner),effect('timers',['door'],timer)]);model['actions'].append(row)
        r=expand_action_model(initial,model,corpus,max_states=16)
        combinations={(s['fields']['inventory']['value'].get('key'),s['fields']['timers']['value'].get('door')) for s in r['states'].values()}
        self.assertTrue({('actor-a',1),('actor-b',1),('actor-a',2)}<=combinations)
    def test_state_transition_step_and_byte_limits_are_explicit(self):
        for kwargs in [dict(max_states=1),dict(max_transitions=1,max_steps=1),dict(max_steps=1),dict(max_state_bytes=1)]:
            initial,model,corpus=fixture()
            with self.subTest(kwargs=kwargs):
                if kwargs.get('max_state_bytes')==1:
                    with self.assertRaises(Hold):expand_action_model(initial,model,corpus,**kwargs)
                else:self.assertTrue(expand_action_model(initial,model,corpus,**kwargs)['truncated'])
    def test_noop_cycles_terminate_by_state_identity(self):
        initial,model,corpus=fixture();model['actions'][0].update(guards=[],effects=[effect('globals',['won'],False)])
        r=expand_action_model(initial,model,corpus);self.assertEqual(len(r['states']),1);self.assertEqual(r['steps_used'],2)
    def test_model_and_initial_input_not_mutated(self):
        initial,model,corpus=fixture();before=copy.deepcopy((initial,model,corpus))
        expand_action_model(initial,model,corpus);self.assertEqual((initial,model,corpus),before)
    def test_report_is_deterministic_and_budget_bound(self):
        initial,model,corpus=fixture();a=expand_action_model(initial,model,corpus);b=expand_action_model(initial,model,corpus)
        self.assertEqual(a,b);self.assertNotEqual(a['exploration_digest'],expand_action_model(initial,model,corpus,max_states=16)['exploration_digest'])
    def test_unknown_model_operations_and_claimed_execution_forbidden(self):
        for key,value in [('effects',[dict(op='shell',field='scripts',path=[],value='do-not-run')]),('guards',[condition('globals',[True],False)])]:
            initial,model,corpus=fixture();model['actions'][0][key]=value
            with self.assertRaises(Hold):expand_action_model(initial,model,corpus)
        initial,model,corpus=fixture();initial['runtime_verified']=True
        with self.assertRaises(Hold):expand_action_model(initial,model,corpus)
    def test_declared_failure_is_not_a_success_path(self):
        initial,model,corpus=fixture();model['endings'][0]['kind']='FAILURE'
        r=expand_action_model(initial,model,corpus);self.assertEqual(r['action_witnesses'],{});self.assertEqual(len(r['failure_candidates']),1)
    def test_dictionary_delete_effect(self):
        initial,model,corpus=fixture();initial['fields']['inventory']['value']={'key':'actor'};initial=typed_state('SYNTHETIC',initial['fields'])
        model['actions'][0]['effects']=[dict(op='delete',field='inventory',path=['key']),effect('globals',['won'],True)]
        r=expand_action_model(initial,model,corpus);end=next(iter(r['success_candidates']))
        self.assertEqual(r['states'][end]['fields']['inventory']['value'],{})
    def test_multistep_ownership_timer_and_object_path(self):
        initial,model,corpus=fixture();cells=initial['fields']
        cells['inventory']['value']={'key':'actor-a'};cells['timers']['value']={'elapsed':0};cells['objects']['value']={'door':False}
        initial=typed_state('SYNTHETIC',cells);base=copy.deepcopy(model['actions'][0])
        handoff=copy.deepcopy(base);handoff.update(id='handoff',guards=[condition('inventory',['key'],'actor-a')],effects=[effect('inventory',['key'],'actor-b'),effect('timers',['elapsed'],1)])
        opened=copy.deepcopy(base);opened.update(id='open',guards=[condition('inventory',['key'],'actor-b'),condition('objects',['door'],False)],effects=[effect('objects',['door'],True)])
        finish=copy.deepcopy(base);finish.update(id='finish',guards=[condition('objects',['door'],True),condition('timers',['elapsed'],1)],effects=[effect('globals',['won'],True)])
        model['actions']=[finish,opened,handoff]
        r=expand_action_model(initial,model,corpus);path=next(iter(r['action_witnesses'].values()))
        self.assertEqual([s['action_id'] for s in path],['handoff','open','finish'])
        for step in path:
            edge=next(e for e in r['transitions'] if e['from']==step['before'] and e['to']==step['after'] and e['action_id']==step['action_id'])
            self.assertEqual(edge['source_refs_sha256'],digest(r['action_sources'][step['action_id']]))
    def test_truncated_model_cannot_claim_a_dead_end_proof(self):
        initial,model,corpus=fixture();r=expand_action_model(initial,model,corpus,max_states=1)
        self.assertTrue(r['truncated']);self.assertEqual(r['analysis']['dead_end_candidates'],[])
        self.assertEqual(r['confirmed_softlocks'],0);self.assertFalse(r['enumeration_complete'])
    def test_existing_atlas_consumes_expanded_model_without_runtime_promotion(self):
        initial,model,corpus=fixture();ir=dict(schema='OpenRemaster.RLR.LogicIR.v1',project='SYNTHETIC',rooms=[],objects=[],dialogues=[],puzzles=[],endings=[])
        result=action_model_atlas(initial,model,corpus,ir)
        self.assertEqual(result['model_analysis']['schema'],'OpenRemaster.RLR.ExpandedModel.v1')
        self.assertEqual(result['coverage']['runtime'],'UNKNOWN');self.assertFalse(result['may_release'])
        ir['project']='FOREIGN'
        with self.assertRaises(Hold):action_model_atlas(initial,model,corpus,ir)

if __name__=='__main__':unittest.main(verbosity=2)
