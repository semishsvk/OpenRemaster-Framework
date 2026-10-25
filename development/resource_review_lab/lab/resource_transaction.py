"""Disposable same-transaction resource hook; no authenticated provider installed."""
from copy import deepcopy
import hashlib
from admission_boundary_base import canonical
from resource_observation import review_resource_observation
from resource_authority import Hold

def prepare_resource_check(identity_inputs,observation,*,expected_identity,expected_resource,owner_keys,envelope_keys):
    inputs=deepcopy(identity_inputs);obs=deepcopy(observation);identity=deepcopy(expected_identity);resource=deepcopy(expected_resource)
    def reserve(db,grant,request,job_bytes,now):
        if canonical(grant)!=canonical(inputs['grant']) or canonical(request)!=canonical(inputs['poa_request']) or job_bytes!=inputs['job_bytes']:raise Hold('RESOURCE_SIGNED_WORK_MISMATCH')
        row=db.execute('SELECT fence,policy,last_sequence FROM resource_state WHERE authority=? AND source=?',(resource['authority_id'],resource['source_id'])).fetchone()
        if row is None:raise Hold('RESOURCE_AUTHORITY_UNAVAILABLE')
        if type(resource['resource_fence']) is not int or row[0]!=resource['resource_fence'] or row[1]!=resource['policy_version']:raise Hold('RESOURCE_FENCE_OR_POLICY_CHANGED')
        current=dict(resource,last_sequence=row[2])
        reviewed=review_resource_observation(inputs,obs,expected_identity=identity,expected_resource=current,owner_keys=owner_keys,envelope_keys=envelope_keys,now=now)
        if not reviewed['resource_checks_satisfied']:raise Hold('RESOURCE_REVIEW_'+reviewed['reason'])
        claim=dict(schema='OpenRemaster.ResourceLabClaim.v1',scope='DISPOSABLE_RESOURCE_LAB_ONLY',
                   operation_id=grant['operation_id'],project=grant['project'],authority_id=resource['authority_id'],source_id=resource['source_id'],
                   sequence=obs['sequence'],owner_epoch=grant['owner_epoch'],owner_fence=grant['fence_generation'],
                   resource_fence=row[0],policy_epoch=grant['policy_epoch'],policy_version=row[1],valid_until=obs['valid_until'],
                   work_identity_sha256=reviewed['evidence']['work_identity_sha256'],observation_sha256=reviewed['evidence']['observation_sha256'],
                   resource_context_sha256=reviewed['evidence']['resource_context_sha256'],resource_review_sha256=hashlib.sha256(canonical(reviewed)).hexdigest(),
                   independent_resource_authority_verified=False,may_dispatch=False,production_go=False)
        raw=canonical(claim);digest=hashlib.sha256(raw).hexdigest()
        db.execute('UPDATE resource_state SET last_sequence=? WHERE authority=? AND source=?',(obs['sequence'],resource['authority_id'],resource['source_id']))
        db.execute('INSERT INTO resource_claims VALUES(?,?,?,?,?,?)',(grant['operation_id'],resource['authority_id'],resource['source_id'],obs['sequence'],raw.decode(),digest))
        return claim
    return reserve
