"""Offline contract lint only. Never an admission, trust or release authority.

Inputs are UNTRUSTED assertions, including apparent verification booleans.
Even a complete fixture receives HOLD pending independent authority adapters.
No execution, lease mutation, credentials, signing, network or publication.
"""
import hashlib
import json
import re

STATES=('DEVELOPMENT','CANDIDATE','VERIFIED','RELEASE_AUTHORIZED','SIGNED','PUBLISHED')
CHECKS=('identity','credentials','attestation','owner_lease','project_scope',
        'single_writer','source_integrity','dependencies','fidelity','regression',
        'security','provenance','release_authorization','signing_authorization',
        'production_available','no_fallback','governor','heartbeat','clean_rebuild')
HANDOFF=('repository','commit','project','build_recipe_sha256','dependencies_sha256',
         'test_profile','candidate_evidence','source_integrity','fidelity_requirements',
         'security_policy_version','release_request')
ZERO=dict(may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,
          may_fallback=False,production_go=False)

def evaluate(document):
    """Return a serializable auditable HOLD/REJECT for every bounded JSON input."""
    reasons=[]
    try:
        raw=json.dumps(document,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        if len(raw)>250000:raise ValueError('oversize')
        digest=hashlib.sha256(raw).hexdigest()
    except (ValueError,TypeError,RecursionError):
        return dict(schema='OpenRemaster.DualTrustShadowDecision.v1',decision='REJECT',
                    reasons=['INVALID_JSON_INPUT'],mode='SHADOW_ONLY',**ZERO)
    if type(document) is not dict:
        reasons.append('OBJECT_REQUIRED');document={}
    before=document.get('from');after=document.get('to')
    if before not in STATES or after not in STATES or STATES.index(after)!=STATES.index(before)+1:
        reasons.append('INVALID_STATE_TRANSITION')
    worker=document.get('worker',{})
    if type(worker) is not dict:worker={}
    trust=worker.get('trust_class')
    if trust not in ('DEVELOPMENT','SECURE_PRODUCTION'):reasons.append('UNKNOWN_TRUST_CLASS')
    if trust=='DEVELOPMENT' and after!='CANDIDATE':reasons.append('DEVELOPMENT_RELEASE_FORBIDDEN')
    if worker.get('requested_trust_class',trust)!=trust:reasons.append('TRUST_ESCALATION_FORBIDDEN')
    if not isinstance(worker.get('identity'),str) or not worker.get('identity'):reasons.append('IDENTITY_MISSING')
    handoff=document.get('handoff',{})
    if type(handoff) is not dict:handoff={}
    for key in HANDOFF:
        value=handoff.get(key)
        if not value or not isinstance(value,(str,list,dict)):reasons.append('HANDOFF_MISSING:'+key)
    if not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',str(handoff.get('commit',''))):
        reasons.append('IMMUTABLE_COMMIT_REQUIRED')
    for field in ('build_recipe_sha256','dependencies_sha256'):
        if not re.fullmatch('[0-9a-f]{64}',str(handoff.get(field,''))):reasons.append('INVALID_DIGEST:'+field)
    checks=document.get('observations',{})
    if type(checks) is not dict:checks={}
    for key in CHECKS:
        # No truthy strings/numbers; these still are assertions, never verified trust.
        if checks.get(key) is not True:reasons.append('EVIDENCE_HOLD:'+key)
    if document.get('fallback_requested') is not False:reasons.append('FALLBACK_FORBIDDEN_OR_UNKNOWN')
    if after=='PUBLISHED' and checks.get('artifact_signature') is not True:reasons.append('UNSIGNED_PUBLICATION_FORBIDDEN')
    # No caller-controlled positive report can cross the trust boundary.
    reasons.append('INDEPENDENT_AUTHORITY_ADAPTERS_NOT_CONNECTED')
    return dict(schema='OpenRemaster.DualTrustShadowDecision.v1',decision='REJECT' if any(x in reasons for x in ('INVALID_STATE_TRANSITION','DEVELOPMENT_RELEASE_FORBIDDEN','TRUST_ESCALATION_FORBIDDEN')) else 'HOLD',
                reasons=sorted(set(reasons)),input_sha256=digest,mode='SHADOW_ONLY',**ZERO)
