"""Review two existing proof domains against explicit context; no authority conversion."""
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
from pathlib import Path
from admission_boundary_base import canonical
from resource_anchor import review_resource_anchor
from openremaster.m012_independent_head_witness import verify_independent_witness,WitnessHold
import openremaster.m012_independent_head_witness as m012
PINNED_M012='337a9581f56762dd3a9f8d23b3e1813026494522022a1c35ec563f771f2b7b83'

RESOURCE_ARGS={'store','anchor','expected','trusted_current','verifier','now'}
WITNESS_ARGS={'receipt','receipt_trust','receipt_authority','witness','witness_trust',
              'expected_witness_authority','expected_challenge','expected_scope','now'}
MAPPING={'schema','resource_anchor_sha256','resource_state_sha256','resource_scope','ledger_id',
         'resource_challenge','resource_sequence','resource_authority_id','receipt_sha256','witness_sha256',
         'recovery_authority_id','witness_authority_id','recovery_scope','recovery_operation_id',
         'recovery_probe_id','recovery_challenge','recovery_result','receipt_sequence','witness_sequence',
         'witness_epoch','witness_fence','receipt_trust_generation','witness_trust_generation'}

def review_resource_witness(resource_args,witness_args,*,expected_mapping=None):
    evidence={}
    def outcome(reason,checks=False):
        return dict(schema='OpenRemaster.ResourceWitnessCrosswalkReview.v1',decision='HOLD',reason=reason,
                    crosswalk_checks_satisfied=checks,evidence=deepcopy(evidence),scope='OFFLINE_TWO_PROOF_CONTEXT_REVIEW',
                    independently_signed_crosswalk=False,resource_signer_domain_independent=False,
                    externally_current_highwater_verified=False,independent_authority_verified=False,
                    dispatch_authorized=False,worker_execution_authorized=False,may_dispatch=False,may_sign=False,
                    may_publish=False,may_promote=False,may_fallback=False,automatic_retry=False,production_go=False)
    if type(resource_args) is not dict or set(resource_args)!=RESOURCE_ARGS:return outcome('RESOURCE_PROOF_INPUT_SCHEMA')
    if type(witness_args) is not dict or set(witness_args)!=WITNESS_ARGS:return outcome('WITNESS_PROOF_INPUT_SCHEMA')
    if type(expected_mapping) is not dict or set(expected_mapping)!=MAPPING:return outcome('EXPLICIT_CROSS_DOMAIN_MAPPING_REQUIRED')
    try:source_sha=hashlib.sha256(Path(m012.__file__).read_bytes()).hexdigest()
    except (OSError,TypeError,ValueError):return outcome('M012_SOURCE_PIN_UNAVAILABLE')
    if source_sha!=PINNED_M012:return outcome('M012_CORRECTED_VERIFIER_PIN_REQUIRED')
    evidence['m012_verifier_source_sha256']=source_sha
    try:
        expected_mapping=deepcopy(expected_mapping);witness_args=deepcopy(witness_args)
        resource_args=dict(resource_args,anchor=deepcopy(resource_args['anchor']),expected=deepcopy(resource_args['expected']))
        if len(canonical(expected_mapping))>16384:return outcome('CROSSWALK_CONTEXT_BOUND')
        now=witness_args['now'];resource_now=resource_args['now']
        if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None or type(resource_now) is not int or now.astimezone(timezone.utc).timestamp()!=resource_now:return outcome('PROOF_CLOCK_CONTEXT_MISMATCH')
        # Real existing verifiers; never accept callers' precomputed PASS decisions.
        verified=verify_independent_witness(**witness_args)
        resource=review_resource_anchor(**resource_args)
        if not resource['anchor_checks_satisfied']:return outcome('RESOURCE_'+resource['reason'])
        anchor=resource_args['anchor'];receipt=witness_args['receipt'];witness=witness_args['witness']
        actual=dict(schema='OpenRemaster.ResourceRecoveryMapping.v1',
                    resource_anchor_sha256=resource['evidence']['presented_anchor_sha256'],
                    resource_state_sha256=resource['evidence']['local_state_sha256'],
                    resource_scope=anchor['scope_id'],ledger_id=anchor['ledger_id'],
                    resource_challenge=anchor['challenge'],resource_sequence=anchor['sequence'],
                    resource_authority_id=anchor['authority_id'],receipt_sha256=verified['receipt_sha256'],
                    witness_sha256=verified['witness_sha256'],recovery_authority_id=witness_args['receipt_authority'],
                    witness_authority_id=witness_args['expected_witness_authority'],recovery_scope=receipt['scope'],
                    recovery_operation_id=receipt['operation_id'],recovery_probe_id=receipt['probe_id'],
                    recovery_challenge=receipt['challenge'],recovery_result=receipt['result'],
                    receipt_sequence=receipt['sequence'],witness_sequence=witness['observed_sequence'],
                    witness_epoch=witness['observed_epoch'],witness_fence=witness['observed_fence'],
                    receipt_trust_generation=receipt['trust_generation'],witness_trust_generation=witness['trust_generation'])
        if canonical(actual)!=canonical(expected_mapping):return outcome('EXPLICIT_MAPPING_MISMATCH')
        evidence.update(mapping_sha256=hashlib.sha256(canonical(actual)).hexdigest(),
                        resource_review_sha256=hashlib.sha256(canonical(resource)).hexdigest(),
                        independent_witness_review_sha256=hashlib.sha256(canonical(verified)).hexdigest())
        return outcome('UNAUTHENTICATED_CROSS_DOMAIN_MAPPING_NO_EXECUTION',True)
    except WitnessHold:return outcome('M012_SIGNATURE_TRUST_OR_BINDING_HOLD')
    except (TypeError,ValueError,KeyError,OverflowError,RecursionError):return outcome('MALFORMED_CROSS_DOMAIN_PROOF')
