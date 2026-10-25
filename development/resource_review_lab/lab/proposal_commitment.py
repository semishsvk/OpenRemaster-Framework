"""Verify an intent commitment inside already signed job bytes, offline only."""
import hashlib,json
from admission_boundary_base import canonical
from proposal_binding import review as review_binding

DOMAIN='OpenRemaster.NamedDevIntentCommitment.v1'
def intent_digest(proposal):
    # The excluded field is checked against the exact signed job bytes below.
    body={k:v for k,v in proposal.items() if k!='job_bytes_sha256'}
    return hashlib.sha256(canonical(dict(schema=DOMAIN,intent=body))).hexdigest()

def strict_job(raw):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('DUPLICATE_JOB_KEY')
            result[key]=value
        return result
    def reject(_):raise ValueError('NONFINITE_JOB_VALUE')
    if type(raw) is not bytes or not 0<len(raw)<=65536:raise ValueError('JOB_BOUND')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=reject)

def review_committed_proposal(proposal,inputs,observation,**context):
    evidence={}
    def outcome(reason):
        return dict(schema='OpenRemaster.NamedDevCommittedReview.v1',decision='HOLD',reason=reason,evidence=dict(evidence),commitment_checks_satisfied=reason=='SIGNED_JOB_INTENT_BOUND_SHADOW_ONLY',independent_authority_verified=False,broker_called=False,nonce_reserved=False,may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,production_go=False)
    try:
        binding=review_binding(proposal,inputs,observation,**context)
        evidence['binding_review_sha256']=hashlib.sha256(canonical(binding)).hexdigest()
        if not binding['binding_checks_satisfied']:return outcome('BINDING_'+binding['reason'])
        job=strict_job(inputs['job_bytes'])
        if type(job) is not dict:return outcome('JOB_SHAPE')
        commitment=job.get('development_intent')
        if type(commitment) is not dict or set(commitment)!={'schema','intent_sha256'}:return outcome('JOB_INTENT_COMMITMENT_REQUIRED')
        if commitment['schema']!=DOMAIN:return outcome('JOB_INTENT_COMMITMENT_VERSION')
        expected=intent_digest(proposal)
        if commitment['intent_sha256']!=expected:return outcome('SIGNED_JOB_INTENT_MISMATCH')
        evidence.update(intent_sha256=expected,proposal_sha256=hashlib.sha256(canonical(proposal)).hexdigest(),job_bytes_sha256=hashlib.sha256(inputs['job_bytes']).hexdigest())
        return outcome('SIGNED_JOB_INTENT_BOUND_SHADOW_ONLY')
    except (KeyError,TypeError,ValueError,OSError,RecursionError,OverflowError):return outcome('MALFORMED_OR_UNAVAILABLE_COMMITMENT')
