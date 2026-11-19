"""Bounded freshness/identity review over the existing offline Governor.

No resource authority, reservation, telemetry collector or scheduler is created.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
from admission_boundary_base import canonical
from work_identity import review_work_identity
from governor import Governor,Telemetry,Job

RESOURCE_CONTEXT={'authority_id','source_id','policy_version','owner_fence','resource_fence',
                  'last_sequence','max_age_seconds','work_identity_sha256'}
OBSERVATION={'schema','authority_id','source_id','policy_version','project_id','operation_id',
             'owner_fence','resource_fence','work_identity_sha256','sequence','observed_at',
             'valid_until','telemetry','jobs'}
TELEMETRY={'cpu_pct','gpu_pct','ram_pct','vram_pct','cpu_temp_c','gpu_temp_c','game_detected'}
JOB={'job_id','heavy','checkpointable','state','checkpoint_sha256'}
def _int(value,low=0,high=2**63-1):return type(value) is int and low<=value<=high
def _text(value):return type(value) is str and 0<len(value)<=256
def _digest(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def _hash(value):return hashlib.sha256(canonical(value)).hexdigest()

def review_resource_observation(identity_inputs,observation,*,expected_identity=None,
                                 expected_resource=None,owner_keys=None,envelope_keys=None,now=None):
    evidence={};proposal=None
    def result(decision,reason,checks=False):
        return dict(schema='OpenRemaster.ResourceObservationReview.v1',decision=decision,reason=reason,
                    resource_checks_satisfied=checks,evidence=deepcopy(evidence),proposal=deepcopy(proposal),
                    scope='OFFLINE_SHADOW_OBSERVATION_ONLY',independent_authority_verified=False,
                    resource_authority_verified=False,observation_consumed=False,nonce_reserved=False,
                    dispatch_authorized=False,may_dispatch=False,may_sign=False,may_publish=False,
                    may_promote=False,may_fallback=False,automatic_retry=False,production_go=False)
    if type(identity_inputs) is not dict or set(identity_inputs)!={'envelope','request','grant','poa_request','job_bytes'}:return result('REJECT','IDENTITY_INPUT_SCHEMA')
    expected_identity=deepcopy(expected_identity)
    identity=review_work_identity(**identity_inputs,expected=expected_identity,owner_keys=owner_keys,envelope_keys=envelope_keys,now=now)
    if not identity['identity_checks_satisfied']:return result(identity['decision'],'IDENTITY_'+identity['reason'])
    evidence['work_identity_sha256']=_hash(identity)
    if type(expected_resource) is not dict or set(expected_resource)!=RESOURCE_CONTEXT:return result('HOLD','RESOURCE_CONTEXT_REQUIRED')
    expected_resource=deepcopy(expected_resource)
    if not all(_text(expected_resource[k]) for k in ('authority_id','source_id','policy_version')) or not all(_int(expected_resource[k],1) for k in ('owner_fence','resource_fence')) or not _int(expected_resource['last_sequence']) or not _int(expected_resource['max_age_seconds'],1,30) or not _digest(expected_resource['work_identity_sha256']):return result('HOLD','RESOURCE_CONTEXT_INVALID')
    context=expected_identity['shadow_context'];binding=identity['bindings']
    for key,expected in [('owner_fence',context['fence']),('resource_fence',context['resource_fence']),('policy_version',context['policy_version']),('work_identity_sha256',evidence['work_identity_sha256'])]:
        if canonical(expected_resource[key])!=canonical(expected):return result('REJECT','RESOURCE_CONTEXT_MISMATCH_'+key.upper())
    if type(observation) is not dict or set(observation)!=OBSERVATION:return result('REJECT','OBSERVATION_SCHEMA')
    try:
        observation=deepcopy(observation)
        if len(canonical(observation))>262144:return result('REJECT','OBSERVATION_BOUND')
        evidence['observation_sha256']=_hash(observation);evidence['resource_context_sha256']=_hash(expected_resource)
        if observation['schema']!='OpenRemaster.ResourceObservation.v1':return result('REJECT','OBSERVATION_VERSION')
        for key in ('authority_id','source_id','policy_version','owner_fence','resource_fence','work_identity_sha256'):
            if canonical(observation[key])!=canonical(expected_resource[key]):return result('REJECT','OBSERVATION_BINDING_MISMATCH_'+key.upper())
        if observation['project_id']!=binding['project'] or observation['operation_id']!=binding['operation_id']:return result('REJECT','OBSERVATION_WORK_SCOPE_MISMATCH')
        if not _int(observation['sequence'],1) or observation['sequence']<=expected_resource['last_sequence']:return result('REJECT','OBSERVATION_SEQUENCE_REPLAY_OR_STALE')
        start,end=observation['observed_at'],observation['valid_until'];age=expected_resource['max_age_seconds']
        if not _int(start,0,253402300799) or not _int(end,0,253402300799):return result('REJECT','OBSERVATION_TIME_TYPE')
        if start>now:return result('REJECT','OBSERVATION_FROM_FUTURE')
        if not start<=now<end or not 0<end-start<=age or now-start>age:return result('HOLD','OBSERVATION_STALE_OR_INVALID_INTERVAL')
        if type(observation['telemetry']) is not dict or set(observation['telemetry'])!=TELEMETRY:return result('REJECT','TELEMETRY_SCHEMA')
        rows=observation['jobs']
        if type(rows) is not list or len(rows)>1024:return result('REJECT','JOB_BOUND')
        jobs=[]
        for row in rows:
            if type(row) is not dict or set(row)!=JOB or type(row['job_id']) is not str or not 0<len(row['job_id'])<=128:return result('REJECT','JOB_SCHEMA')
            jobs.append(Job(**row))
        target=[j for j in jobs if j.job_id==binding['job_id']]
        if len(target)!=1 or target[0].heavy is not binding['heavy']:return result('REJECT','TARGET_JOB_BINDING_MISMATCH')
        proposal=asdict(Governor().plan(Telemetry(**observation['telemetry']),jobs))
        if any(j.state=='UNKNOWN' for j in jobs):return result('HOLD','UNKNOWN_EXECUTION_NO_RETRY')
        if proposal['mode']!='NORMAL':return result('HOLD','GOVERNOR_'+proposal['mode'])
        if target[0].state!='WAITING':return result('HOLD','TARGET_NOT_WAITING')
        if binding['job_id'] not in proposal['admit']:return result('HOLD','CAPACITY_OR_GOVERNOR_HOLD')
        return result('HOLD','RESOURCE_AUTHORITY_UNAVAILABLE',True)
    except (TypeError,ValueError,KeyError,OverflowError,RecursionError):return result('REJECT','INVALID_RESOURCE_OBSERVATION')
