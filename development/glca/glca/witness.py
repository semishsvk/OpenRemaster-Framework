"""Linear checking of supplied declarative paths; never authentic runtime replay."""
from .core import require,canonical_state_bytes,digest
from .retail import typed_state
from .transitions import validate_action_model,_condition,_apply

def verify_model_witness(initial,model,corpus,witness,*,max_steps=1024):
    require(type(max_steps) is int and 0<max_steps<=4096,'WITNESS_BOUND')
    checked=validate_action_model(model,corpus)
    require(type(initial) is dict and initial.get('project')==checked['project'],'INITIAL_PROJECT')
    state=typed_state(initial['project'],initial.get('fields'))
    require(canonical_state_bytes(state)==canonical_state_bytes(initial),'INITIAL_STATE_IDENTITY')
    canonical_state_bytes(witness)
    require(type(witness) is dict and set(witness)=={'schema','project','model_digest','source_manifest_digest','initial_state','steps','final_state','ending_id'},'WITNESS_SCHEMA')
    require(witness['schema']=='OpenRemaster.RLR.ModelWitness.v1','WITNESS_VERSION')
    for key in ('project','model_digest','source_manifest_digest'):
        require(witness[key]==checked[key],'WITNESS_CONTEXT')
    require(witness['initial_state']==state['state_digest'],'WITNESS_INITIAL')
    steps=witness['steps'];require(type(steps) is list and len(steps)<=max_steps,'WITNESS_STEP_BOUND')
    require(type(witness['ending_id']) is str and 0<len(witness['ending_id'])<=128,'WITNESS_ENDING_ID')
    actions={a['id']:a for a in model['actions']}
    def terminal(current):
        results=[(ending,_condition(current,ending['guards'])) for ending in model['endings']]
        require(all(result is not None for _,result in results),'WITNESS_TERMINAL_UNKNOWN')
        enabled=[ending for ending,result in results if result is True]
        require(len({e['kind'] for e in enabled})<=1,'CONTRADICTORY_TERMINAL_PREDICATES')
        return enabled
    for step in steps:
        require(type(step) is dict and set(step)=={'before','after','action_id'},'WITNESS_STEP_SCHEMA')
        require(not terminal(state),'WITNESS_ACTION_AFTER_TERMINAL')
        require(step['before']==state['state_digest'],'WITNESS_BEFORE')
        require(type(step['action_id']) is str and step['action_id'] in actions,'WITNESS_ACTION')
        action=actions[step['action_id']]
        require(_condition(state,action['guards']) is True,'WITNESS_GUARD_NOT_TRUE')
        target=_apply(state,action)
        require(target is not None,'WITNESS_EFFECT_UNKNOWN')
        require(step['after']==target['state_digest'],'WITNESS_AFTER')
        state=target
    require(witness['final_state']==state['state_digest'],'WITNESS_FINAL')
    endings=terminal(state)
    require(any(e['id']==witness['ending_id'] and e['kind']=='SUCCESS' for e in endings),'WITNESS_SUCCESS_NOT_ESTABLISHED')
    return dict(schema='OpenRemaster.RLR.ModelWitnessResult.v1',status='STATIC_CANDIDATE',
                witness_digest=digest(witness),model_digest=checked['model_digest'],
                final_state=state['state_digest'],steps_checked=len(steps),
                scope='SUPPLIED_DECLARATIVE_MODEL_ONLY',original_game_validated=False,
                native_roundtrip_verified=False,may_dispatch=False,may_release=False,
                may_sign=False,may_publish=False,may_promote=False,may_fallback=False)
