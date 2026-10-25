"""RLR contracts over the existing GLCA model. All results are source/model-only.

This module cannot discover game semantics, admit workers or prove runtime fidelity.
"""
from collections import deque
import hashlib
import json
from pathlib import Path
import re
from .core import require, digest, reachability, canonical_state_bytes

FIELDS=('location','inventory','objects','globals','npcs','timers','scripts','save','terminal')
EVIDENCE_STATES=('SOURCE_ONLY','STATIC_CANDIDATE','RUNTIME_REFERENCE_VERIFIED',
                 'REMASTER_REPLAY_VERIFIED','INDEPENDENT_ACCEPTED','UNKNOWN','HOLD')

def corpus_manifest(root, *, project, max_files=4096, max_bytes=256*1024*1024):
    """Explicit bounded read-only hashing. Never executes or decodes source files."""
    requested=Path(root)
    require(not requested.is_symlink(),'CORPUS_LINK_FORBIDDEN')
    root=requested.resolve(strict=True)
    require(root.is_dir() and type(project) is str and bool(project),'CORPUS_IDENTITY')
    require(type(max_files) is int and 0<max_files<=100000,'FILE_BOUND')
    require(type(max_bytes) is int and 0<max_bytes<=4*1024**3,'BYTE_BOUND')
    records=[];total=0
    # Bounded traversal, including directories; sorted per directory for repeatability.
    pending=[root];visited=0
    while pending:
        directory=pending.pop();visited+=1
        require(visited<=max_files*4,'DIRECTORY_BOUND')
        children=sorted(directory.iterdir(),key=lambda p:p.name)
        require(len(children)<=max_files*4,'DIRECTORY_ENTRY_BOUND')
        for p in children:
            require(not p.is_symlink(),'CORPUS_LINK_FORBIDDEN')
            require(p.resolve().is_relative_to(root),'CORPUS_PATH_ESCAPE')
            if p.is_dir():pending.append(p);continue
            require(p.is_file(),'UNSUPPORTED_CORPUS_ENTRY')
            require(len(records)<max_files,'FILE_BOUND')
            before=p.stat();total+=before.st_size
            require(total<=max_bytes,'BYTE_BOUND')
            h=hashlib.sha256();count=0
            with p.open('rb') as stream:
                for block in iter(lambda:stream.read(65536),b''):
                    count+=len(block);require(count<=before.st_size,'SOURCE_CHANGED_DURING_HASH')
                    h.update(block)
            after=p.stat()
            require((before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
                    and count==before.st_size,'SOURCE_CHANGED_DURING_HASH')
            records.append(dict(path=p.relative_to(root).as_posix(),bytes=count,sha256=h.hexdigest(),
                                format='UNKNOWN',decoder_coverage='UNKNOWN',confidence='UNKNOWN'))
    records.sort(key=lambda r:r['path'])
    return dict(schema='OpenRemaster.RLR.CorpusManifest.v1',project=project,files=records,
                bytes=total,manifest_digest=digest([project,records]),status='SOURCE_ONLY',
                runtime_verified=False)

def typed_state(project, fields):
    """Retain actor/item/timer/save distinctions and explicit unknown values."""
    require(type(project) is str and bool(project),'PROJECT_REQUIRED')
    require(type(fields) is dict and set(fields)==set(FIELDS),'STATE_FIELDS')
    result={}
    for key,value in fields.items():
        require(type(value) is dict and set(value) in ({'known','value'},{'known'}),'TYPED_VALUE_REQUIRED')
        require(type(value['known']) is bool,'KNOWN_BOOLEAN_REQUIRED')
        if value['known']:
            require('value' in value and value['value'] is not None,'KNOWN_VALUE_REQUIRED')
        else:require(set(value)=={'known'},'UNKNOWN_VALUE_FORBIDDEN')
        result[key]=value
    # JSON preserves false/0 and timer/owner distinctions; caller data are detached.
    raw=canonical_state_bytes(result)
    detached=json.loads(raw)
    state=dict(schema='OpenRemaster.RLR.StateIR.v1',project=project,fields=detached)
    return dict(**state,state_digest=digest(state),complete=all(v['known'] for v in detached.values()),
                runtime_verified=False)

def validate_ir(project, document, corpus):
    """World/object/dialogue/puzzle/ending catalog with source-range provenance."""
    require(type(document) is dict and document.get('schema')=='OpenRemaster.RLR.LogicIR.v1','IR_SCHEMA')
    require(document.get('project')==project==corpus.get('project'),'CROSS_PROJECT_IR')
    require(corpus.get('schema')=='OpenRemaster.RLR.CorpusManifest.v1','CORPUS_SCHEMA')
    files={f['path']:f for f in corpus['files']}
    categories=('rooms','objects','dialogues','puzzles','endings')
    require(all(type(document.get(k)) is list for k in categories),'IR_CATEGORIES')
    require(sum(len(document[k]) for k in categories)<=100000,'IR_BOUND')
    known=set();references=[]
    for category in categories:
        for row in document[category]:
            require(type(row) is dict and type(row.get('id')) is str and bool(row['id']),'IR_ID')
            ident=(category,row['id']);require(ident not in known,'DUPLICATE_IR_ID');known.add(ident)
            require(row.get('evidence_state') in ('SOURCE_ONLY','STATIC_CANDIDATE','UNKNOWN','HOLD'),
                    'INDEPENDENT_PROMOTION_VERIFIER_REQUIRED')
            refs=row.get('source_refs')
            require(type(refs) is list and bool(refs),'SOURCE_REFS_REQUIRED')
            for ref in refs:
                require(type(ref) is dict and ref.get('path') in files,'SOURCE_FILE_UNKNOWN')
                file=files[ref['path']]
                require(ref.get('sha256')==file['sha256'] and re.fullmatch('[a-f0-9]{64}',ref['sha256']),
                        'SOURCE_HASH_MISMATCH')
                start,length=ref.get('offset'),ref.get('length')
                require(type(start) is int and type(length) is int and start>=0 and length>0
                        and start+length<=file['bytes'],'SOURCE_RANGE_INVALID')
            links=row.get('links',[]);require(type(links) is list,'IR_LINKS')
            for link in links:
                require(type(link) is dict and set(link)=={'kind','id'}
                        and type(link['kind']) is str and type(link['id']) is str,'IR_LINK_SCHEMA')
                references.append((link['kind'],link['id']))
    require(all(link in known for link in references),'DANGLING_IR_LINK')
    return dict(schema='OpenRemaster.RLR.IRValidation.v1',status='SOURCE_ONLY',
                project=project,records=len(known),ir_digest=digest(document),
                semantic_completeness='UNKNOWN',runtime_verified=False,confirmed_softlocks=0)

def solve_model(states, transitions, start, endings, *, complete=False, limit=4096):
    """Reuse GLCA reachability and attach reproducible certain-edge witnesses."""
    result=reachability(states,transitions,start,endings,complete=complete,limit=limit)
    parents={start:None};queue=deque([start]);edges={s:[] for s in states}
    for edge in transitions:
        if edge.get('guard') is True:edges[edge['from']].append(edge['to'])
    while queue:
        src=queue.popleft()
        for target in sorted(edges[src]):
            if target not in parents:
                parents[target]=src;queue.append(target)
    witnesses={};steps=0
    for target in sorted(endings):
        if target not in parents:continue
        cursor=target;path=[]
        while parents[cursor] is not None:
            steps+=1;require(steps<=limit*16,'WITNESS_BOUND')
            prior=parents[cursor];path.append(dict(before=prior,after=cursor));cursor=prior
        witnesses[target]=list(reversed(path))
    result['path_witnesses']=witnesses
    result['witness_scope']='SUPPLIED_MODEL_ONLY_NOT_ORIGINAL_RUNTIME'
    result['model_digest']=digest([states,transitions,start,endings])
    return result

def atlas(project, ir, corpus, model):
    validation=validate_ir(project,ir,corpus)
    return dict(schema='OpenRemaster.RLR.LogicAtlas.v1',project=project,
                source_validation=validation,world=ir['rooms'],objects=ir['objects'],
                dialogues=ir['dialogues'],puzzles=ir['puzzles'],endings=ir['endings'],
                model_analysis=model,coverage=dict(source_records=validation['records'],
                runtime='UNKNOWN',full_game='UNKNOWN'),status='STATIC_CANDIDATE',
                may_dispatch=False,may_release=False)
