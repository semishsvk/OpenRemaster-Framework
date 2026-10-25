import copy,hashlib,unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import test_resource_anchor as resource_fixture
from test_m012_independent_head_witness import fixture,resign
from test_m011_signed_recovery import private_and_trust,sign
from openremaster.m005_anchor_contract import sha256_json
from openremaster.m012_independent_head_witness import verify_independent_witness
from resource_anchor import review_resource_anchor
from admission_boundary_base import canonical
from resource_witness import review_resource_witness
import resource_witness as bridge
from unittest.mock import patch

class ResourceWitnessTests(unittest.TestCase):
    def setUp(self):
        self.r=resource_fixture.ResourceAnchorTests(methodName='test_matching_anchor_still_shadow_hold');self.r.setUp();self.addCleanup(self.r.doCleanups)
        self.wkey,self.w=fixture();now=datetime.fromtimestamp(self.r.f.f.now,timezone.utc)
        stamp=lambda d:d.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.pkey,trust=private_and_trust();trust=replace(trust,expires_utc=stamp(now+timedelta(seconds=300)))
        receipt=self.w['receipt'];receipt.update(issued_utc=stamp(now-timedelta(seconds=10)),expires_utc=stamp(now+timedelta(seconds=25)));sign(self.pkey,receipt)
        self.w.update(receipt_trust=trust,now=now)
        witness=self.w['witness'];witness.update(m011_receipt_sha256=sha256_json(receipt),issued_utc=stamp(now-timedelta(seconds=4)),expires_utc=stamp(now+timedelta(seconds=20)))
        self.w['witness_trust']=replace(self.w['witness_trust'],expires_utc=stamp(now+timedelta(seconds=300)));resign(self.wkey,witness)
        self.resource=dict(store=self.r.store,anchor=self.r.presented,expected=self.r.expected,trusted_current=self.r.provider,verifier=self.r.verify,now=self.r.f.f.now)
        rv=review_resource_anchor(**self.resource);wv=verify_independent_witness(**self.w);a=self.r.presented
        self.mapping=dict(schema='OpenRemaster.ResourceRecoveryMapping.v1',resource_anchor_sha256=rv['evidence']['presented_anchor_sha256'],resource_state_sha256=rv['evidence']['local_state_sha256'],resource_scope=a['scope_id'],ledger_id=a['ledger_id'],resource_challenge=a['challenge'],resource_sequence=a['sequence'],resource_authority_id=a['authority_id'],receipt_sha256=wv['receipt_sha256'],witness_sha256=wv['witness_sha256'],recovery_authority_id=self.w['receipt_authority'],witness_authority_id=self.w['expected_witness_authority'],recovery_scope=receipt['scope'],recovery_operation_id=receipt['operation_id'],recovery_probe_id=receipt['probe_id'],recovery_challenge=receipt['challenge'],recovery_result=receipt['result'],receipt_sequence=receipt['sequence'],witness_sequence=witness['observed_sequence'],witness_epoch=witness['observed_epoch'],witness_fence=witness['observed_fence'],receipt_trust_generation=receipt['trust_generation'],witness_trust_generation=witness['trust_generation'])
    def call(self,**kw):return review_resource_witness(self.resource,self.w,expected_mapping=kw.get('mapping',self.mapping))
    def test_matching_proofs_are_not_an_authenticated_mapping(self):
        r=self.call();self.assertTrue(r['crosswalk_checks_satisfied']);self.assertEqual(r['decision'],'HOLD')
        self.assertEqual(r['reason'],'UNAUTHENTICATED_CROSS_DOMAIN_MAPPING_NO_EXECUTION')
        for key in ('independently_signed_crosswalk','resource_signer_domain_independent','externally_current_highwater_verified','independent_authority_verified','dispatch_authorized','worker_execution_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[key],False)
    def test_no_implicit_mapping_when_context_missing(self):self.assertEqual(self.call(mapping=None)['reason'],'EXPLICIT_CROSS_DOMAIN_MAPPING_REQUIRED')
    def test_every_mapping_field_is_exact(self):
        for key in self.mapping:
            m=copy.deepcopy(self.mapping);m[key]=m[key]+1 if type(m[key]) is int else 'different'
            self.assertEqual(self.call(mapping=m)['reason'],'EXPLICIT_MAPPING_MISMATCH',key)
    def test_resource_snapshot_cannot_be_relabelled_as_recovery_head(self):
        m=dict(self.mapping,resource_state_sha256=self.w['receipt']['remote_head_sha256'])
        self.assertNotEqual(m['resource_state_sha256'],self.mapping['resource_state_sha256']);self.assertEqual(self.call(mapping=m)['reason'],'EXPLICIT_MAPPING_MISMATCH')
    def test_key_alias_collision_is_rejected_by_reused_m012(self):
        t=self.w['witness_trust'];keys=dict(t.keys);keys['receipt-role-alias']=next(iter(self.w['receipt_trust'].public_keys.values()))
        self.w['witness_trust']=replace(t,keys=keys);self.assertEqual(self.call()['reason'],'M012_SIGNATURE_TRUST_OR_BINDING_HOLD')
    def test_revoked_witness_holds(self):
        t=self.w['witness_trust'];self.w['witness_trust']=replace(t,revoked=frozenset([self.w['witness']['key_id']]))
        self.assertEqual(self.call()['reason'],'M012_SIGNATURE_TRUST_OR_BINDING_HOLD')
    def test_stale_trust_generation_holds(self):
        t=self.w['witness_trust'];self.w['witness_trust']=replace(t,generation=t.generation+1)
        self.assertEqual(self.call()['reason'],'M012_SIGNATURE_TRUST_OR_BINDING_HOLD')
    def test_expired_trust_holds(self):
        t=self.w['witness_trust'];self.w['witness_trust']=replace(t,expires_utc=self.w['now'].strftime('%Y-%m-%dT%H:%M:%SZ'))
        self.assertEqual(self.call()['reason'],'M012_SIGNATURE_TRUST_OR_BINDING_HOLD')
    def test_changed_signed_challenge_rejected(self):
        self.w['witness']['challenge']='different_challenge_0123456789';resign(self.wkey,self.w['witness'])
        self.assertEqual(self.call()['reason'],'M012_SIGNATURE_TRUST_OR_BINDING_HOLD')
    def test_old_signed_head_cannot_match_new_expected_sequence(self):
        self.assertEqual(self.call(mapping=dict(self.mapping,witness_sequence=3))['reason'],'EXPLICIT_MAPPING_MISMATCH')
    def test_clock_context_mismatch_holds(self):
        self.resource['now']+=1;self.assertEqual(self.call()['reason'],'PROOF_CLOCK_CONTEXT_MISMATCH')
    def test_local_rollback_with_unchanged_external_highwater_holds(self):
        self.r.restore();self.assertEqual(self.call()['reason'],'RESOURCE_LOCAL_ROLLBACK_OR_DRIFT')
    def test_missing_resource_provider_never_falls_back_to_m012(self):
        self.resource['trusted_current']=None;self.assertEqual(self.call()['reason'],'RESOURCE_NO_INDEPENDENT_AUTHORITY')
    def test_resource_signature_failure_holds(self):
        self.r.current['signature']='0'*64;self.resource['anchor']=copy.deepcopy(self.r.current)
        self.assertEqual(self.call()['reason'],'RESOURCE_UNTRUSTED_CURRENT_ANCHOR')
    def test_precomputed_pass_cannot_replace_signed_proof(self):
        self.w={'status':'TWO_SIGNATURES_CROSS_BOUND_REVIEW_ONLY'};self.assertEqual(self.call()['reason'],'WITNESS_PROOF_INPUT_SCHEMA')
    def test_mapping_schema_cannot_gain_authority_fields(self):
        m=dict(self.mapping,may_dispatch=True);self.assertEqual(self.call(mapping=m)['reason'],'EXPLICIT_CROSS_DOMAIN_MAPPING_REQUIRED')
    def test_inputs_are_not_mutated(self):
        before=copy.deepcopy((self.mapping,self.w));self.call();self.assertEqual(before,(self.mapping,self.w))
    def test_unpinned_or_legacy_verifier_source_is_hold(self):
        with patch.object(bridge.m012,'__file__',__file__):self.assertEqual(self.call()['reason'],'M012_CORRECTED_VERIFIER_PIN_REQUIRED')
