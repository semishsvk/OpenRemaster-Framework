import copy,hashlib,unittest
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch
from admission_boundary_base import canonical
from rejection_evidence import rejection_record,export_bundle
from rejection_witness import DOMAIN,mapping_digest,review_witnessed_import
import rejection_witness as bridge
import test_m012_independent_head_witness as fixture
from test_m011_signed_recovery import private_and_trust,make_receipt,sign
from openremaster.m005_anchor_contract import sha256_json

class RejectionWitnessTests(unittest.TestCase):
    def setUp(self):
        record=rejection_record(dict(decision='HOLD',reason='STALE_OWNER_LEASE'),dict(attempt_id='a'*32,operation_id=None,input_digests=dict(job_sha256=None,request_sha256=None,proposal_sha256=None)),observed_at=1800000000)
        self.raw=canonical(export_bundle([record]));self.key,self.proof=fixture.fixture()
        self.receipt_key,trust=private_and_trust();self.proof['receipt']=make_receipt(self.receipt_key,challenge=self.proof['expected_challenge']);self.proof['receipt_trust']=trust
        p=self.proof;r=p['receipt'];w=p['witness']
        self.context=dict(source_revision='a'*40,scope=r['scope'],operation_id=r['operation_id'],probe_id=r['probe_id'],challenge=r['challenge'],receipt_authority=p['receipt_authority'],witness_authority=p['expected_witness_authority'],minimum_sequence=2,receipt_trust_generation=r['trust_generation'],witness_trust_generation=w['trust_generation'])
        self.mapping=dict(self.context,schema=DOMAIN,snapshot_bytes_sha256=hashlib.sha256(self.raw).hexdigest(),record_count=1,receipt_sequence=r['sequence'],recovery_result=r['result']);self.resign()
    def resign(self):
        r=self.proof['receipt'];r['request_sha256']=mapping_digest(self.mapping);sign(self.receipt_key,r)
        self.proof['witness']['m011_receipt_sha256']=sha256_json(r);fixture.resign(self.key,self.proof['witness'])
    def call(self):return review_witnessed_import(self.raw,self.proof,mapping=self.mapping,expected_context=self.context)
    def test_signed_mapping_matches_but_never_grants_independent_authority(self):
        r=self.call();self.assertTrue(r['mapping_checks_satisfied'],r);self.assertEqual(r['decision'],'HOLD')
        for key in ('independent_authority_verified','external_currentness_verified','source_revision_verified','authenticated_audit_storage_verified','durability_verified','complete_history_verified','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[key],False)
    def test_uncommitted_mapping_does_not_inherit_witness_trust(self):
        self.proof['receipt']['request_sha256']='f'*64;sign(self.receipt_key,self.proof['receipt']);self.proof['witness']['m011_receipt_sha256']=sha256_json(self.proof['receipt']);fixture.resign(self.key,self.proof['witness'])
        self.assertEqual(self.call()['reason'],'M011_REQUEST_DOES_NOT_COMMIT_AUDIT_MAPPING')
    def test_changed_snapshot_cannot_reuse_signed_mapping(self):
        self.raw+=b' ';self.assertFalse(self.call()['mapping_checks_satisfied'])
    def test_changed_mapping_needs_new_signatures(self):
        self.mapping['snapshot_bytes_sha256']='f'*64;self.assertEqual(self.call()['reason'],'M011_REQUEST_DOES_NOT_COMMIT_AUDIT_MAPPING')
    def test_missing_context_and_precomputed_proof_hold(self):
        self.context=None;self.assertEqual(self.call()['reason'],'EXTERNAL_MAPPING_CONTEXT_REQUIRED');self.context={};self.proof={'verified':True};self.assertEqual(self.call()['reason'],'EXISTING_WITNESS_INPUT_REQUIRED')
    def test_wrong_domain_even_when_resigned_holds(self):
        self.mapping['schema']='RECOVERY_HEAD_IS_AUDIT';self.resign();self.assertEqual(self.call()['reason'],'MAPPING_DOMAIN_MISMATCH')
    def test_source_revision_cannot_drift_from_expected_context(self):
        self.mapping['source_revision']='b'*40;self.resign();self.assertEqual(self.call()['reason'],'EXTERNAL_MAPPING_CONTEXT_MISMATCH')
    def test_mutable_source_ref_not_allowed(self):
        self.context['source_revision']='main';self.mapping['source_revision']='main';self.resign();self.assertEqual(self.call()['reason'],'IMMUTABLE_SOURCE_REVISION_REQUIRED')
    def test_sequence_floor_blocks_old_signed_snapshot(self):
        self.context['minimum_sequence']=3;self.mapping['minimum_sequence']=3;self.resign();self.assertEqual(self.call()['reason'],'EXPECTED_SEQUENCE_FLOOR_HOLD')
    def test_expired_or_future_proofs_hold(self):
        self.proof['now']+=timedelta(seconds=60);self.assertEqual(self.call()['reason'],'EXISTING_SIGNATURE_TRUST_OR_FRESHNESS_HOLD')
    def test_revoked_key_holds(self):
        t=self.proof['witness_trust'];self.proof['witness_trust']=replace(t,revoked=frozenset([self.proof['witness']['key_id']]));self.assertFalse(self.call()['mapping_checks_satisfied'])
    def test_key_alias_overlap_holds(self):
        t=self.proof['witness_trust'];keys=dict(t.keys);keys['receipt-role-alias']=next(iter(self.proof['receipt_trust'].public_keys.values()));self.proof['witness_trust']=replace(t,keys=keys);self.assertEqual(self.call()['reason'],'EXISTING_SIGNATURE_TRUST_OR_FRESHNESS_HOLD')
    def test_wrong_challenge_holds(self):
        self.proof['expected_challenge']='q'*24;self.assertFalse(self.call()['mapping_checks_satisfied'])
    def test_trust_generation_mismatch_holds(self):
        t=self.proof['witness_trust'];self.proof['witness_trust']=replace(t,generation=3);self.assertFalse(self.call()['mapping_checks_satisfied'])
    def test_recovery_head_is_not_snapshot_digest(self):
        self.assertNotEqual(self.proof['receipt']['remote_head_sha256'],self.mapping['snapshot_bytes_sha256']);self.assertTrue(self.call()['mapping_checks_satisfied'])
    def test_source_pins_fail_closed(self):
        with patch.object(bridge.m012,'__file__',__file__):self.assertEqual(self.call()['reason'],'EXISTING_VERIFIER_SOURCE_PIN_REQUIRED')
    def test_boolean_counter_rejects(self):
        self.context['minimum_sequence']=True;self.mapping['minimum_sequence']=True;self.resign();self.assertEqual(self.call()['reason'],'MAPPING_COUNTER_TYPE')
    def test_input_not_mutated(self):
        before=copy.deepcopy((self.proof,self.mapping,self.context));self.call();self.assertEqual(before,(self.proof,self.mapping,self.context))
