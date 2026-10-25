"""Bounded positional trace diagnostics; never original-runtime attestation."""
import hashlib
from evidence_cache_v1 import CacheHold,require,sha,strict_json
from vendor.evidence_behavior import BehaviorEvent,BehaviorReplay,evaluate_behavior,REQUIRED_BEHAVIOR

SCHEMA='OpenRemaster.BehaviorTraceDocument.v1'

def text(value,limit):
    return type(value) is str and 0<len(value)<=limit and all(ord(c)>=32 and not 0xD800<=ord(c)<=0xDFFF for c in value)

def parse(raw,expected_sha):
    require(type(raw) is bytes and len(raw)<=1024*1024,'TRACE_BYTES_LIMIT')
    require(sha(expected_sha) and hashlib.sha256(raw).hexdigest()==expected_sha,'TRACE_HASH_MISMATCH')
    doc=strict_json(raw)
    require(type(doc) is dict and set(doc)=={'schema','project','corpus_sha256','capture_point','witness_sha256','events'} and doc['schema']==SCHEMA,'TRACE_SCHEMA')
    require(text(doc['project'],160) and text(doc['capture_point'],160) and sha(doc['corpus_sha256']) and sha(doc['witness_sha256']),'TRACE_IDENTITY')
    require(type(doc['events']) is list and 0<len(doc['events'])<=4096,'EVENT_COUNT')
    for event in doc['events']:
        require(type(event) is dict and set(event)=={'tick','kind','effect'},'EVENT_SCHEMA')
        require(type(event['tick']) is int and 0<=event['tick']<=2**53-1 and text(event['kind'],64) and text(event['effect'],1024),'EVENT_VALUE')
    return doc

def diagnose(original_bytes,candidate_bytes,original_sha,candidate_sha,expected,*,tick_tolerance=0):
    base={'schema':'OpenRemaster.FirstDivergence.v1','status':'HOLD','may_dispatch':False,
          'can_claim_fidelity_verified':False,'can_claim_playable':False,
          'alignment_method':'POSITIONAL_NO_RESYNCHRONIZATION','original_runtime_attested':False}
    try:
        require(type(tick_tolerance) is int and 0<=tick_tolerance<=2**53-1,'INVALID_TOLERANCE')
        require(type(expected) is dict and set(expected)=={'project','corpus_sha256','capture_point'} and text(expected['project'],160) and text(expected['capture_point'],160) and sha(expected['corpus_sha256']),'EXPECTED_IDENTITY')
        a=parse(original_bytes,original_sha);b=parse(candidate_bytes,candidate_sha)
        require(all(d[k]==v for d in (a,b) for k,v in expected.items()),'IDENTITY_MISMATCH')
        events=lambda d:tuple(BehaviorEvent(**e) for e in d['events'])
        replay=BehaviorReplay(a['project'],a['corpus_sha256'],original_sha,candidate_sha,a['witness_sha256'],b['witness_sha256'],a['capture_point'],a['capture_point'],b['capture_point'],events(a),events(b))
        decision=evaluate_behavior(replay,tick_tolerance=tick_tolerance)
        result={**base,'input_sha256':{'original':original_sha,'candidate':candidate_sha},
                'identity':dict(expected),'tick_tolerance':tick_tolerance,'legacy_decision':decision}
        if decision['reason'] not in ('BEHAVIOR_MISMATCH','REQUIRES_INDEPENDENT_ORIGINAL_AND_NATIVE_ATTESTATION'):
            return {**result,'reason':decision['reason']}
        original,candidate=a['events'],b['events']
        index=None;fields=[]
        for i,(x,y) in enumerate(zip(original,candidate)):
            differing=[k for k in ('kind','effect') if x[k]!=y[k]]
            if abs(x['tick']-y['tick'])>tick_tolerance:differing.append('tick')
            if differing:index=i;fields=differing;break
        if index is None and len(original)!=len(candidate):index=min(len(original),len(candidate));fields=['event_presence']
        if index is None:return {**result,'reason':'PROVIDED_EVENTS_MATCH','compared_events':len(original),'first_difference':None}
        def side(rows,raw_sha):
            present=index<len(rows)
            return {'sha256':raw_sha,'pointer':f'/events/{index}' if present else None,'event':dict(rows[index]) if present else None,
                    'end_pointer':'/events' if not present else None,
                    'context':[{'index':i,'event':dict(rows[i])} for i in range(max(0,index-2),min(len(rows),index+3))]}
        difference={'index':index,'fields':fields,'original':side(original,original_sha),'candidate':side(candidate,candidate_sha)}
        if index<min(len(original),len(candidate)):difference['candidate_minus_original_tick']=candidate[index]['tick']-original[index]['tick']
        return {**result,'reason':'FIRST_DIVERGENCE_LOCATED','first_difference':difference,
                'lengths':{'original':len(original),'candidate':len(candidate)},
                'byte_offsets_available':False,'root_cause_proven':False}
    except CacheHold as exc:
        return {**base,'reason':str(exc),'first_difference':None}
