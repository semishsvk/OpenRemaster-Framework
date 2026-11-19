"""Bounded export of reported HOLD/REJECT evidence, never an authorization log."""
import hashlib,re
from copy import deepcopy
from admission_boundary_base import canonical

REASONS=frozenset({'UNKNOWN_WORKER_IDENTITY','INVALID_CREDENTIALS','MISSING_ATTESTATION','WRONG_TRUST_CLASS','STALE_OWNER_LEASE','UNAUTHORIZED_PROJECT','CONCURRENT_WRITER','SOURCE_HASH_MISMATCH','DEPENDENCY_HASH_MISMATCH','MISSING_FIDELITY_GATE','INCOMPLETE_PROVENANCE','INVALID_SIGNING_AUTHORIZATION','DEVELOPMENT_RELEASE_ATTEMPT','TRUST_ESCALATION_ATTEMPT','PRODUCTION_WORKER_UNAVAILABLE','RELEASE_FALLBACK_ATTEMPT','OWNER_EPOCH_GENERATION_LEASE_OR_SOURCE_HOLD','RESOURCE_OPERATION_ALREADY_PRESENT_QUERY_ONLY','RESOURCE_FENCE_OR_POLICY_CHANGED','NONCE_JOB_OR_OPERATION_REPLAY_CONFLICT','GAME_WIP_LIMIT_DENIED','FOURTH_HEAVY_SLOT_DENIED','RESOURCE_REVIEW_GOVERNOR_LIGHT_GAMING','AUDIT_EXPORT_UNAVAILABLE','UNCLASSIFIED_FAILURE'})
P8_REASONS=frozenset({'INPUT_SCHEMA_HOLD','WINDOWS_LOCK_UNAVAILABLE_HOLD','JOURNAL_IO_HOLD','LOCK_TIMEOUT_HOLD','PARTIAL_JOURNAL_HOLD','JOURNAL_JSON_OR_SCHEMA_HOLD','JOURNAL_EVENT_SCHEMA_HOLD','HASH_CHAIN_HOLD','JOURNAL_HISTORY_REPLAY_HOLD','JOURNAL_BOUND_HOLD','SHADOW_RESERVATION_NOT_AUTHORITY','JOURNAL_REPLAY_QUERY_ONLY','JOURNAL_WRITE_UNCERTAIN_QUERY_ONLY','UNRECOGNIZED_JOURNAL_STATUS','UNEXPECTED_PROVIDER_FAILURE'})
REASONS=REASONS|P8_REASONS
HASHES={'job_sha256','request_sha256','proposal_sha256'}
CONTEXT={'attempt_id','operation_id','input_digests'}
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def hexvalue(value,length):return type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None

def rejection_record(decision,context,*,observed_at):
    if type(decision) is not dict or set(decision)!={'decision','reason'} or decision['decision'] not in ('HOLD','REJECT') or type(decision['reason']) is not str or not 0<len(decision['reason'])<=512:raise ValueError('REJECTION_DECISION_INVALID')
    if type(context) is not dict or set(context)!=CONTEXT or not hexvalue(context['attempt_id'],32) or (context['operation_id'] is not None and not hexvalue(context['operation_id'],32)):raise ValueError('REJECTION_CONTEXT_INVALID')
    refs=context['input_digests']
    if type(refs) is not dict or set(refs)!=HASHES or any(v is not None and not hexvalue(v,64) for v in refs.values()):raise ValueError('REJECTION_DIGEST_REFS_INVALID')
    if type(observed_at) is not int or not 0<=observed_at<=253402300799:raise ValueError('REJECTION_TIME_INVALID')
    body=dict(schema='OpenRemaster.ShadowRejectionEvidence.v1',scope='REPORTED_SHADOW_DECISION_NOT_INDEPENDENT_AUDIT',decision=decision['decision'],reason_code=decision['reason'] if decision['reason'] in REASONS else 'UNCLASSIFIED_FAILURE',observed_at=observed_at,**deepcopy(context),independent_authority_verified=False,durability_verified=False,transaction_outcome='NOT_ATTESTED',may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,automatic_retry=False,production_go=False)
    return dict(body,record_sha256=digest(body))

def record_p8_status(status,context,*,observed_at):
    """Record an already reported scalar status through the existing boundary."""
    from p8_failclosed import observe_journal_status
    reported=observe_journal_status(status)
    return rejection_record(dict(decision='HOLD',reason=reported['reason_code']),context,observed_at=observed_at)

def validate_record(record):
    if type(record) is not dict:raise ValueError('REJECTION_RECORD_INVALID')
    try:
        expected=rejection_record(dict(decision=record['decision'],reason=record['reason_code']),{k:record[k] for k in CONTEXT},observed_at=record['observed_at'])
        if canonical(record)!=canonical(expected):raise ValueError('REJECTION_RECORD_MISMATCH')
    except (KeyError,TypeError,RecursionError) as e:raise ValueError('REJECTION_RECORD_INVALID') from e
    return deepcopy(record)

def export_bundle(records):
    if type(records) is not list or not 1<=len(records)<=128:raise ValueError('REJECTION_EXPORT_BOUND')
    validated=[validate_record(r) for r in records]
    attempts=[r['attempt_id'] for r in validated]
    if len(set(attempts))!=len(attempts):raise ValueError('DUPLICATE_REJECTION_ATTEMPT')
    body=dict(schema='OpenRemaster.ShadowRejectionExport.v1',records=validated,record_count=len(validated),independent_authority_verified=False,authenticated=False,durability_verified=False,complete_history_verified=False,may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,production_go=False)
    return dict(body,export_sha256=digest(body))
