"""Offline explicit mapping bound by existing M011/M012 proof domains."""
import hashlib,re
from copy import deepcopy
from pathlib import Path
from admission_boundary_base import canonical
from rejection_import import review_import
from rejection_evidence import hexvalue
import openremaster.m012_independent_head_witness as m012
import openremaster.m011_signed_recovery as m011

DOMAIN='OpenRemaster.RejectionSnapshotWitnessMapping.v1'
CONTEXT={'source_revision','scope','operation_id','probe_id','challenge','receipt_authority','witness_authority','minimum_sequence','receipt_trust_generation','witness_trust_generation'}
MAPPING=CONTEXT|{'schema','snapshot_bytes_sha256','record_count','receipt_sequence','recovery_result'}
ARGS={'receipt','receipt_trust','receipt_authority','witness','witness_trust','expected_witness_authority','expected_challenge','expected_scope','now'}
PINS={'m012':'337a9581f56762dd3a9f8d23b3e1813026494522022a1c35ec563f771f2b7b83','m011':'2ade013adc064e0c7face0c56b615d72bcf94b2cbd0450ceb5fd71b9e1369496'}
def mapping_digest(mapping):return hashlib.sha256(canonical(mapping)).hexdigest()
def review_witnessed_import(raw,proof,*,mapping=None,expected_context=None):
    evidence={}
    def outcome(reason,checks=False):
        return dict(schema='OpenRemaster.RejectionWitnessReview.v1',decision='HOLD',reason=reason,mapping_checks_satisfied=checks,evidence=dict(evidence),independent_authority_verified=False,external_currentness_verified=False,source_revision_verified=False,authenticated_audit_storage_verified=False,durability_verified=False,complete_history_verified=False,may_dispatch=False,may_sign=False,may_publish=False,may_promote=False,may_fallback=False,automatic_retry=False,production_go=False)
    if type(proof) is not dict or set(proof)!=ARGS:return outcome('EXISTING_WITNESS_INPUT_REQUIRED')
    if type(expected_context) is not dict or set(expected_context)!=CONTEXT:return outcome('EXTERNAL_MAPPING_CONTEXT_REQUIRED')
    if type(mapping) is not dict or set(mapping)!=MAPPING:return outcome('EXPLICIT_SIGNED_MAPPING_REQUIRED')
    try:
        for name,module in [('m012',m012),('m011',m011)]:
            if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()!=PINS[name]:return outcome('EXISTING_VERIFIER_SOURCE_PIN_REQUIRED')
        context=deepcopy(expected_context);mapping=deepcopy(mapping);proof=deepcopy(proof)
        if len(canonical(mapping))>8192 or len(canonical(context))>8192:return outcome('MAPPING_CONTEXT_BOUND')
        if mapping['schema']!=DOMAIN:return outcome('MAPPING_DOMAIN_MISMATCH')
        revision=context['source_revision']
        if type(revision) is not str or re.fullmatch('[0-9a-f]{40}',revision) is None or revision=='0'*40:return outcome('IMMUTABLE_SOURCE_REVISION_REQUIRED')
        for key in ('minimum_sequence','receipt_trust_generation','witness_trust_generation'):
            if type(context[key]) is not int or not 1<=context[key]<2**63-1:return outcome('MAPPING_COUNTER_TYPE')
        if canonical({k:mapping[k] for k in CONTEXT})!=canonical(context):return outcome('EXTERNAL_MAPPING_CONTEXT_MISMATCH')
        verified=m012.verify_independent_witness(**proof)
        receipt=proof['receipt'];witness=proof['witness']
        actual=dict(scope=receipt['scope'],operation_id=receipt['operation_id'],probe_id=receipt['probe_id'],challenge=receipt['challenge'],receipt_authority=proof['receipt_authority'],witness_authority=proof['expected_witness_authority'],receipt_trust_generation=receipt['trust_generation'],witness_trust_generation=witness['trust_generation'],receipt_sequence=receipt['sequence'],recovery_result=receipt['result'])
        if canonical({k:mapping[k] for k in actual})!=canonical(actual):return outcome('SIGNED_PROOF_MAPPING_MISMATCH')
        if receipt['sequence']<context['minimum_sequence']:return outcome('EXPECTED_SEQUENCE_FLOOR_HOLD')
        committed=mapping_digest(mapping)
        if receipt['request_sha256']!=committed:return outcome('M011_REQUEST_DOES_NOT_COMMIT_AUDIT_MAPPING')
        imported=review_import(raw,expected_bytes_sha256=mapping['snapshot_bytes_sha256'],expected_record_count=mapping['record_count'])
        if not imported['integrity_matched']:return outcome('IMPORT_'+imported['reason'])
        evidence.update(mapping_sha256=committed,snapshot_bytes_sha256=imported['evidence']['observed_bytes_sha256'],witness_review_sha256=mapping_digest(verified),receipt_sha256=verified['receipt_sha256'],witness_sha256=verified['witness_sha256'],record_count=imported['evidence']['record_count'])
        return outcome('SIGNED_MAPPING_AND_BYTES_MATCH_SHADOW_ONLY',True)
    except m012.WitnessHold:return outcome('EXISTING_SIGNATURE_TRUST_OR_FRESHNESS_HOLD')
    except (KeyError,TypeError,ValueError,OSError,RecursionError,OverflowError):return outcome('MALFORMED_OR_UNAVAILABLE_MAPPING_PROOF')
