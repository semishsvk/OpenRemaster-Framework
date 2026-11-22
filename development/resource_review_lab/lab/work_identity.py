"""Read-only dual-format identity review. No grant conversion or admission I/O."""
from copy import deepcopy
import hashlib
import authority as poa
from admission_shadow import evaluate_shadow_admission,CONTEXT
from admission_boundary_base import canonical

def review_work_identity(envelope,request,grant,poa_request,job_bytes,*,expected=None,
                         owner_keys=None,envelope_keys=None,now=None):
    evidence={}
    def outcome(decision,reason,bindings=None):
        return dict(schema='OpenRemaster.WorkIdentityReview.v1',decision=decision,reason=reason,
                    identity_checks_satisfied=bindings is not None,bindings=deepcopy(bindings),
                    evidence=deepcopy(evidence),scope='ISOLATED_SHADOW_IDENTITY_ONLY',
                    independent_authority_verified=False,resource_authority_verified=False,
                    nonce_reserved=False,dispatch_authorized=False,may_dispatch=False,
                    may_sign=False,may_publish=False,may_promote=False,may_fallback=False,
                    automatic_retry=False,production_go=False)
    if type(expected) is not dict or set(expected)!={'binding','shadow_context'}:return outcome('HOLD','EXPECTED_IDENTITY_REQUIRED')
    if type(expected['binding']) is not dict or set(expected['binding'])!=set(poa.BIND):return outcome('HOLD','EXPECTED_BINDING_INCOMPLETE')
    if type(expected['shadow_context']) is not dict or set(expected['shadow_context'])!=CONTEXT:return outcome('HOLD','EXPECTED_CONTEXT_INCOMPLETE')
    if type(now) is not int or not 0<=now<=253402300799:return outcome('HOLD','VERIFIED_CLOCK_REQUIRED')
    if type(job_bytes) is not bytes or not 0<len(job_bytes)<=65536:return outcome('REJECT','JOB_BYTES_INVALID')
    if type(owner_keys) is not dict or type(envelope_keys) is not dict or not owner_keys or not envelope_keys:return outcome('HOLD','PINNED_KEY_REGISTRIES_REQUIRED')
    if not all(type(k) is str and type(v) is bytes and len(v)>=32 for k,v in owner_keys.items()) or not all(type(k) is str and type(v) is bytes and len(v)==32 for k,v in envelope_keys.items()):return outcome('HOLD','KEY_REGISTRY_INVALID')
    if set(owner_keys.values()) & set(envelope_keys.values()):return outcome('REJECT','SIGNING_DOMAIN_KEY_MATERIAL_OVERLAP')
    try:
        expected=deepcopy(expected);grant=deepcopy(grant);poa_request=deepcopy(poa_request)
        for document in (expected,grant,poa_request):
            if len(canonical(document))>65536:return outcome('REJECT','IDENTITY_DOCUMENT_BOUND')
        scope,_=poa.verify_grant(grant,owner_keys,now)
        poa.verify_request(grant,poa_request,job_bytes,scope)
        # Python == would conflate True/1. Preserve exact JSON types across every BIND field.
        binding={key:grant[key] for key in poa.BIND}
        if canonical(binding)!=canonical(expected['binding']):return outcome('REJECT','EXPECTED_BINDING_MISMATCH')
        if canonical({key:poa_request[key] for key in poa.BIND})!=canonical(binding):return outcome('REJECT','REQUEST_BINDING_TYPE_MISMATCH')
        context=expected['shadow_context']
        pairs={'operation_id':'operation_id','project_id':'project','capability':'scenario',
               'fence':'fence_generation','lease_id':'lease_id'}
        for shadow,key in pairs.items():
            if canonical(context[shadow])!=canonical(binding[key]):return outcome('REJECT','CROSSWALK_MISMATCH_'+shadow.upper())
        if type(envelope) is not dict or envelope.get('nonce')!=binding['nonce']:return outcome('REJECT','NONCE_CROSSWALK_MISMATCH')
        shadow=evaluate_shadow_admission(envelope,request,envelope_keys,expected=context,authority=None,now=now)
        evidence.update(shadow['evidence'])
        if shadow['reason']!='AUTHORITY_UNAVAILABLE':return outcome(shadow['decision'],'SHADOW_'+shadow['reason'])
        evidence.update(owner_grant_sha256=hashlib.sha256(canonical(grant)).hexdigest(),
                        poa_request_sha256=hashlib.sha256(canonical(poa_request)).hexdigest(),
                        job_sha256=hashlib.sha256(job_bytes).hexdigest(),
                        full_binding_sha256=hashlib.sha256(canonical(binding)).hexdigest(),
                        expected_identity_sha256=hashlib.sha256(canonical(expected)).hexdigest())
        return outcome('HOLD','RESOURCE_AUTHORITY_UNAVAILABLE',binding)
    except poa.Hold as exc:return outcome('REJECT','POAV2_'+str(exc))
    except (KeyError,TypeError,ValueError,OverflowError,RecursionError):return outcome('REJECT','MALFORMED_IDENTITY')
