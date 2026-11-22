"""Compose the existing disposable resource hook with signed intent verification."""
from copy import deepcopy
from admission_boundary_base import canonical
from proposal_commitment import review_committed_proposal
from resource_transaction import prepare_resource_check
from resource_authority import Hold

def prepare_committed_resource_check(proposal,inputs,observation,*,expected_identity,expected_resource,recipe_pins,owner_keys,envelope_keys):
    proposal=deepcopy(proposal);inputs=deepcopy(inputs);observation=deepcopy(observation)
    context=deepcopy(dict(expected_identity=expected_identity,expected_resource=expected_resource,recipe_pins=recipe_pins,owner_keys=owner_keys,envelope_keys=envelope_keys))
    base=prepare_resource_check(inputs,observation,**{k:v for k,v in context.items() if k!='recipe_pins'})
    def reserve(db,grant,request,job_bytes,now):
        if canonical(grant)!=canonical(inputs['grant']) or canonical(request)!=canonical(inputs['poa_request']) or job_bytes!=inputs['job_bytes']:raise Hold('COMMITTED_SIGNED_WORK_MISMATCH')
        result=review_committed_proposal(proposal,inputs,observation,now=now,**context)
        if not result['commitment_checks_satisfied']:raise Hold('COMMITTED_PROPOSAL_'+result['reason'])
        # Existing hook rechecks current resource state/highwater in this transaction.
        # Existing ACK/event job_sha256 binds the committed intent; no new store/claim schema.
        return base(db,grant,request,job_bytes,now)
    return reserve
