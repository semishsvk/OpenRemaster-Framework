"""Shadow-only context binding over the captured Ed25519 verifier.

Injected authority is a contract port, not a new authority or nonce service.
Even a conforming response grants no execution permission.
"""
from copy import deepcopy
import hashlib
import math
import re
from admission_boundary_base import canonical,verify_before_spawn,AdmissionRejected

CONTEXT={'operation_id','project_id','capability','fence','lease_id','resource_fence',
         'authority_id','policy_version','trust_class'}

def _hash(value):return hashlib.sha256(canonical(value)).hexdigest()
def _text(value):return type(value) is str and 0<len(value)<=256
def _positive(value):return type(value) is int and 0<value<=2**63-1

def evaluate_shadow_admission(envelope,request,trusted_keys,*,expected=None,authority=None,now=None):
    """Return auditable HOLD/REJECT; never dispatch, retry or enable production.

    authority(claim) must atomically check current lease, both fences, project,
    capability, policy and expiry and reserve (issuer, nonce) exactly once.
    Missing/failed/uncertain authority responses stay HOLD without retry.
    expected and trusted_keys must be supplied by a future verified host adapter.
    """
    evidence={}
    def result(decision,reason,checks=False):
        return dict(schema='OpenRemaster.ShadowAdmissionDecision.v1',decision=decision,reason=reason,
                    checks_satisfied=checks,evidence=deepcopy(evidence),scope='SHADOW_CONTRACT_ONLY',
                    independent_authority_verified=False,dispatch_authorized=False,may_dispatch=False,
                    may_sign=False,may_publish=False,may_promote=False,may_fallback=False,
                    automatic_retry=False,production_go=False)
    if type(expected) is not dict or set(expected)!=CONTEXT:return result('HOLD','EXPECTED_CONTEXT_REQUIRED')
    expected=deepcopy(expected)
    if not all(_text(expected[k]) for k in CONTEXT-{'fence','resource_fence'}):return result('HOLD','EXPECTED_CONTEXT_INVALID')
    if not all(_positive(expected[k]) for k in ('fence','resource_fence')):return result('HOLD','EXPECTED_FENCE_INVALID')
    if expected['trust_class']!='DEVELOPMENT':return result('REJECT','DEVELOPMENT_SCOPE_ONLY')
    if expected['capability']!='build_studio_dev':return result('REJECT','CAPABILITY_OUTSIDE_CAPTURED_DEV_SCOPE')
    if not re.fullmatch('[a-f0-9]{32}',expected['operation_id']):return result('HOLD','EXPECTED_OPERATION_INVALID')
    if type(now) not in (int,float) or not 0<=now<=253402300799 or not math.isfinite(now):return result('HOLD','VERIFIED_CLOCK_REQUIRED')
    if type(request) is not dict or set(request)!={'action','operation_id','scenario'}:return result('REJECT','REQUEST_SCHEMA')
    request=deepcopy(request)
    if request['action']!='submit' or request['operation_id']!=expected['operation_id'] or request['scenario']!=expected['capability']:return result('REJECT','REQUEST_CONTEXT_MISMATCH')
    if type(envelope) is not dict:return result('REJECT','ENVELOPE_SCHEMA')
    envelope=deepcopy(envelope)
    try:
        raw=canonical(envelope)
        if len(raw)>16384:return result('REJECT','ENVELOPE_SIZE')
        evidence.update(envelope_sha256=hashlib.sha256(raw).hexdigest(),request_sha256=_hash(request),context_sha256=_hash(expected))
        verify_before_spawn(envelope,request,trusted_keys,now=now)
    except AdmissionRejected as exc:return result('REJECT',str(exc))
    except (TypeError,ValueError,OverflowError,RecursionError):return result('REJECT','MALFORMED_EVIDENCE')
    for key in ('operation_id','project_id','capability','fence'):
        if type(envelope[key]) is not type(expected[key]) or envelope[key]!=expected[key]:return result('REJECT','ENVELOPE_CONTEXT_MISMATCH_'+key.upper())
    claim=dict(schema='OpenRemaster.ShadowNonceReservation.v1',**expected,
               issuer_kid=envelope['issuer_kid'],nonce=envelope['nonce'],not_after=envelope['not_after'],
               envelope_sha256=evidence['envelope_sha256'],request_sha256=evidence['request_sha256'])
    evidence['claim_sha256']=_hash(claim)
    if not callable(authority):return result('HOLD','AUTHORITY_UNAVAILABLE')
    try:receipt=authority(deepcopy(claim))
    except Exception:return result('HOLD','AUTHORITY_RESULT_UNCERTAIN')
    fields={'schema','status','authority_id','claim_sha256','receipt_id','event_sequence'}
    if type(receipt) is not dict or set(receipt)!=fields:return result('HOLD','AUTHORITY_RECEIPT_SCHEMA')
    if receipt['schema']!='OpenRemaster.ShadowNonceReceipt.v1' or receipt['authority_id']!=expected['authority_id'] or receipt['claim_sha256']!=evidence['claim_sha256'] or not _text(receipt['receipt_id']) or not _positive(receipt['event_sequence']):return result('HOLD','AUTHORITY_RECEIPT_MISMATCH')
    if receipt['status'] in ('STALE_LEASE','STALE_FENCE','REPLAY','SCOPE_DENIED','EXPIRED'):return result('REJECT','AUTHORITY_'+receipt['status'])
    if receipt['status']!='RESERVED':return result('HOLD','AUTHORITY_NOT_RESERVED')
    evidence['authority_receipt_sha256']=_hash(receipt)
    return result('HOLD','SHADOW_CHECKS_SATISFIED_NO_EXECUTION',True)
