"""Bounded declarative model expansion over GLCA/RLR, never runtime execution."""
from collections import deque
from copy import deepcopy
import re
from .core import require,canonical_state_bytes,digest
from .retail import FIELDS,typed_state,validate_ir,solve_model,atlas

def _path(path):
    require(type(path) is list and len(path)<=16,'ACTION_PATH_BOUND')
    require(all((type(x) is str and 0<len(x)<=256) or (type(x) is int and 0<=x<=1000000) for x in path),'ACTION_PATH_TYPE')

def _guards(guards,ending=False):
    require(type(guards) is list and (1 if ending else 0)<=len(guards)<=64,'GUARD_BOUND')
    for guard in guards:
        require(type(guard) is dict and set(guard)=={'field','path','equals'},'GUARD_SCHEMA')
        require(guard['field'] in FIELDS,'GUARD_FIELD');_path(guard['path'])
        canonical_state_bytes(guard['equals'])

def validate_action_model(model,corpus):
    """Validate declared semantics and source ranges, not independently proven behavior."""
    canonical_state_bytes(model)
    require(type(model) is dict and set(model)=={'schema','project','source_manifest_digest','actions','endings'},'ACTION_MODEL_SCHEMA')
    require(model['schema']=='OpenRemaster.RLR.ActionModel.v1','ACTION_MODEL_VERSION')
    project=model['project'];require(type(project) is str and 0<len(project)<=256,'MODEL_PROJECT')
    require(type(corpus) is dict and corpus.get('schema')=='OpenRemaster.RLR.CorpusManifest.v1' and corpus.get('project')==project,'MODEL_CORPUS_IDENTITY')
    files=corpus.get('files');require(type(files) is list and len(files)<=4096,'CORPUS_FILE_BOUND')
    paths=set()
    for file in files:
        require(type(file) is dict,'CORPUS_FILE_SCHEMA')
        require(set(file)<={'path','bytes','sha256','format','decoder_coverage','confidence'},'CORPUS_FILE_FIELDS')
        for key in ('format','decoder_coverage','confidence'):
            if key in file:require(type(file[key]) is str and len(file[key])<=256,'CORPUS_METADATA_BOUND')
        path=file.get('path')
        require(type(path) is str and 0<len(path)<=512 and not path.startswith('/') and '\\' not in path and ':' not in path and all(p not in ('','.','..') for p in path.split('/')),'CORPUS_PATH')
        require(path not in paths,'DUPLICATE_CORPUS_PATH');paths.add(path)
        require(type(file.get('bytes')) is int and 0<=file['bytes']<=4*1024**3,'CORPUS_FILE_SIZE')
        require(type(file.get('sha256')) is str and re.fullmatch('[a-f0-9]{64}',file['sha256']) is not None,'CORPUS_FILE_HASH')
    require(files==sorted(files,key=lambda f:f['path']),'CORPUS_ORDER')
    corpus_digest=digest([project,files])
    require(corpus.get('manifest_digest')==corpus_digest==model['source_manifest_digest'],'MODEL_SOURCE_DIGEST_MISMATCH')
    actions=model['actions'];endings=model['endings']
    require(type(actions) is list and len(actions)<=128 and type(endings) is list and len(endings)<=32,'ACTION_MODEL_BOUND')
    ids=set();logic=dict(schema='OpenRemaster.RLR.LogicIR.v1',project=project,rooms=[],objects=[],dialogues=[],puzzles=[],endings=[])
    for kind,records in [('puzzles',actions),('endings',endings)]:
        for row in records:
            fields={'id','guards','effects','source_refs'} if kind=='puzzles' else {'id','guards','kind','source_refs'}
            require(type(row) is dict and set(row)==fields,'ACTION_RECORD_SCHEMA')
            require(type(row['id']) is str and 0<len(row['id'])<=128 and row['id'] not in ids,'ACTION_IDENTITY');ids.add(row['id'])
            _guards(row['guards'],ending=kind=='endings')
            require(type(row['source_refs']) is list and 0<len(row['source_refs'])<=32,'ACTION_SOURCE_BOUND')
            logic[kind].append(dict(id=row['id'],source_refs=row['source_refs'],evidence_state='STATIC_CANDIDATE'))
            if kind=='endings':require(row['kind'] in ('SUCCESS','FAILURE'),'ENDING_KIND');continue
            effects=row['effects'];require(type(effects) is list and 0<len(effects)<=64,'EFFECT_BOUND')
            targets=[]
            for effect in effects:
                require(type(effect) is dict and effect.get('op') in ('set','delete'),'EFFECT_OPERATION')
                require(set(effect)==({'op','field','path','value'} if effect['op']=='set' else {'op','field','path'}),'EFFECT_SCHEMA')
                require(effect['field'] in FIELDS,'EFFECT_FIELD');_path(effect['path'])
                if effect['op']=='set':canonical_state_bytes(effect['value'])
                else:require(bool(effect['path']) and type(effect['path'][-1]) is str,'DELETE_REQUIRES_OBJECT_KEY')
                target=(effect['field'],effect['path'])
                require(not any(f==target[0] and (p==target[1][:len(p)] or target[1]==p[:len(target[1])]) for f,p in targets),'CONFLICTING_EFFECT_TARGETS')
                targets.append(target)
    validate_ir(project,logic,corpus)
    return dict(project=project,model_digest=digest(model),source_manifest_digest=corpus_digest,semantics='CALLER_DECLARED_NOT_RUNTIME_VERIFIED')

def _lookup(state,field,path):
    cell=state['fields'][field]
    if not cell['known']:return False,None
    current=cell['value']
    for key in path:
        if type(current) is dict and type(key) is str and key in current:current=current[key]
        elif type(current) is list and type(key) is int and key<len(current):current=current[key]
        else:return False,None
    return True,current

def _condition(state,guards):
    unknown=False
    for guard in guards:
        known,value=_lookup(state,guard['field'],guard['path'])
        if not known:unknown=True
        elif canonical_state_bytes(value)!=canonical_state_bytes(guard['equals']):return False
    return None if unknown else True

def _apply(state,action):
    fields=deepcopy(state['fields'])
    for effect in action['effects']:
        field=effect['field'];path=effect['path'];cell=fields[field]
        if not path:
            fields[field]={'known':True,'value':deepcopy(effect['value'])};continue
        if not cell['known']:return None
        current=cell['value']
        for key in path[:-1]:
            if type(current) is dict and type(key) is str and key in current:current=current[key]
            elif type(current) is list and type(key) is int and key<len(current):current=current[key]
            else:return None
        key=path[-1]
        if effect['op']=='delete':
            if type(current) is not dict or key not in current:return None
            del current[key]
        elif type(current) is dict and type(key) is str:current[key]=deepcopy(effect['value'])
        elif type(current) is list and type(key) is int and key<len(current):current[key]=deepcopy(effect['value'])
        else:return None
    return typed_state(state['project'],fields)

def expand_action_model(initial,model,corpus,*,max_states=256,max_transitions=4096,max_steps=10000,max_state_bytes=8*1024*1024):
    """Expand only certainly enabled declarative actions; reuse the existing solver."""
    for value,upper in [(max_states,4096),(max_transitions,65536),(max_steps,100000),(max_state_bytes,16*1024*1024)]:
        require(type(value) is int and 0<value<=upper,'EXPLORATION_BOUND')
    checked=validate_action_model(model,corpus)
    require(type(initial) is dict and initial.get('project')==model['project'],'INITIAL_PROJECT')
    rebuilt=typed_state(initial['project'],initial.get('fields'))
    require(canonical_state_bytes(rebuilt)==canonical_state_bytes(initial),'INITIAL_STATE_IDENTITY')
    first=rebuilt['state_digest'];states={first:rebuilt};queue=deque([first]);edges=[];unknowns=[];success={};failure={}
    total_bytes=len(canonical_state_bytes(rebuilt));require(total_bytes<=max_state_bytes,'INITIAL_STATE_BYTE_BOUND')
    steps=0;truncated=False;actions=sorted(model['actions'],key=lambda a:a['id']);endings=sorted(model['endings'],key=lambda e:e['id'])
    edge_limit=min(max_transitions,max_states*16)
    if not endings:unknowns.append(dict(state=first,reason='ENDING_PREDICATE_MISSING'))
    while queue and not truncated:
        ident=queue.popleft();state=states[ident];terminal=[];terminal_unknown=False
        for ending in endings:
            if steps>=max_steps:truncated=True;break
            steps+=1;result=_condition(state,ending['guards'])
            if result is None:terminal_unknown=True;unknowns.append(dict(state=ident,ending=ending['id'],reason='ENDING_GUARD_UNKNOWN'))
            elif result:terminal.append(ending)
        if truncated:break
        kinds={e['kind'] for e in terminal};require(len(kinds)<=1,'CONTRADICTORY_TERMINAL_PREDICATES')
        if terminal_unknown:continue
        if terminal:
            (success if 'SUCCESS' in kinds else failure)[ident]=[e['id'] for e in terminal]
            continue
        for action in actions:
            if steps>=max_steps:truncated=True;break
            steps+=1;enabled=_condition(state,action['guards'])
            if enabled is None:unknowns.append(dict(state=ident,action=action['id'],reason='ACTION_GUARD_UNKNOWN'));continue
            if not enabled:continue
            target=_apply(state,action)
            if target is None:unknowns.append(dict(state=ident,action=action['id'],reason='EFFECT_TARGET_UNKNOWN'));continue
            dest=target['state_digest'];size=len(canonical_state_bytes(target))
            if len(edges)>=edge_limit or (dest not in states and (len(states)>=max_states or total_bytes+size>max_state_bytes)):
                truncated=True;break
            edges.append(dict(**{'from':ident,'to':dest},guard=True,action_id=action['id'],source_refs_sha256=digest(action['source_refs'])))
            if dest not in states:states[dest]=target;total_bytes+=size;queue.append(dest)
    analysis=solve_model(sorted(states),edges,first,sorted(success),complete=False,limit=max_states)
    if unknowns or truncated:analysis['dead_end_candidates']=[]
    edge_actions={}
    for edge in edges:edge_actions.setdefault((edge['from'],edge['to']),[]).append(edge['action_id'])
    witnesses={key:[dict(**step,action_id=sorted(edge_actions[(step['before'],step['after'])])[0]) for step in path] for key,path in analysis['path_witnesses'].items()}
    return dict(
        schema='OpenRemaster.RLR.ExpandedModel.v1',project=model['project'],
        model_digest=checked['model_digest'],
        exploration_digest=digest([checked['model_digest'],first,max_states,edge_limit,max_steps,max_state_bytes]),
        source_manifest_digest=checked['source_manifest_digest'],initial_state=first,
        states=states,transitions=edges,
        action_sources={a['id']:deepcopy(a['source_refs']) for a in actions},
        success_candidates=success,failure_candidates=failure,action_witnesses=witnesses,
        unknowns=unknowns,truncated=truncated,
        enumeration_complete=not truncated and not unknowns,analysis=analysis,
        budget=dict(states=max_states,transitions=edge_limit,steps=max_steps,state_bytes=max_state_bytes),
        steps_used=steps,status='STATIC_CANDIDATE',scope='SUPPLIED_DECLARATIVE_MODEL_ONLY',
        confirmed_softlocks=0,original_game_validated=False,native_roundtrip_verified=False,
        may_dispatch=False,may_release=False)

def action_model_atlas(initial,model,corpus,logic_ir,**bounds):
    """Project the bounded model through the existing source-bound atlas contract."""
    expanded=expand_action_model(initial,model,corpus,**bounds)
    return atlas(model['project'],logic_ir,corpus,expanded)
