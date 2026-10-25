"""Offline binding review; no provider, broker or execution side effects."""
import hashlib,json
from pathlib import Path
from jsonschema import Draft202012Validator
from admission_boundary_base import canonical
from resource_observation import review_resource_observation

PINS={'recipe_sha256','toolchain_manifest_sha256','dependency_lock_sha256'}
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def review(proposal,inputs,observation,*,expected_identity=None,expected_resource=None,recipe_pins=None,owner_keys=None,envelope_keys=None,now=None):
    evidence={}
    def outcome(reason):
        return dict(schema='OpenRemaster.NamedDevBindingReview.v1',decision='HOLD',reason=reason,evidence=dict(evidence),binding_checks_satisfied=reason=='BOUND_SHADOW_ONLY_AUTHORITY_AND_K003_EXTENSION_REQUIRED',independent_authority_verified=False,observation_consumed=False,nonce_reserved=False,broker_called=False,may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,production_go=False)
    try:
        if type(proposal) is not dict or len(canonical(proposal))>16384:return outcome('PROPOSAL_BOUND')
        schema=json.loads((Path(__file__).parent.parent/'schemas/named-dev-build-proposal.schema.json').read_text())
        if list(Draft202012Validator(schema).iter_errors(proposal)):return outcome('PROPOSAL_SCHEMA')
        if type(recipe_pins) is not dict or set(recipe_pins)!=PINS:return outcome('INDEPENDENT_RECIPE_PINS_REQUIRED')
        for key in PINS:
            if type(recipe_pins[key]) is not str or len(recipe_pins[key])!=64 or any(c not in '0123456789abcdef' for c in recipe_pins[key]):return outcome('RECIPE_PINS_INVALID')
            if proposal[key]!=recipe_pins[key]:return outcome('RECIPE_PIN_MISMATCH_'+key.upper())
        reviewed=review_resource_observation(inputs,observation,expected_identity=expected_identity,expected_resource=expected_resource,owner_keys=owner_keys,envelope_keys=envelope_keys,now=now)
        evidence['resource_review_sha256']=digest(reviewed)
        if not reviewed['resource_checks_satisfied']:return outcome('RESOURCE_'+reviewed['reason'])
        request=inputs['request'];binding=expected_identity['binding'];context=expected_identity['shadow_context']
        if type(request) is not dict or set(request)!={'action','operation_id','scenario'}:return outcome('D7_REQUEST_SCHEMA')
        checks={'action':request['action'],'operation_id':request['operation_id'],'capability':request['scenario'],'project':binding['project'],'source_manifest_sha256':binding['source_sha256'],'job_bytes_sha256':hashlib.sha256(inputs['job_bytes']).hexdigest(),'request_sha256':digest(request),'owner_fence_sha256':digest(dict(owner_id=binding['owner_id'],owner_epoch=binding['owner_epoch'],lease_id=binding['lease_id'],fence_generation=binding['fence_generation'])),'resource_fence_sha256':digest(dict(authority_id=expected_resource['authority_id'],source_id=expected_resource['source_id'],policy_version=context['policy_version'],resource_fence=context['resource_fence']))}
        for key,value in checks.items():
            if canonical(proposal[key])!=canonical(value):return outcome('BINDING_MISMATCH_'+key.upper())
        evidence.update(proposal_sha256=digest(proposal),request_sha256=digest(request),job_bytes_sha256=checks['job_bytes_sha256'])
        return outcome('BOUND_SHADOW_ONLY_AUTHORITY_AND_K003_EXTENSION_REQUIRED')
    except (KeyError,TypeError,ValueError,OSError,RecursionError,OverflowError):return outcome('MALFORMED_OR_UNAVAILABLE_EVIDENCE')
