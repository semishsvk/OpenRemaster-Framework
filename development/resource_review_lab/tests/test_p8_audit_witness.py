"""Complete reported P8 snapshot -> unchanged M011/M012 crosswalk, offline."""
import copy,hashlib,json,os,tempfile,unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from admission_boundary_base import canonical
import rejection_evidence as audit
import test_rejection_witness as witness_fixture
import test_p8_audit as audit_fixture
import test_p8_journal as journal_fixture
import p8_journal as journal

REVIEWS=[]
STATES=('INPUT_SCHEMA_HOLD','WINDOWS_LOCK_UNAVAILABLE_HOLD','JOURNAL_IO_HOLD','LOCK_TIMEOUT_HOLD','PARTIAL_JOURNAL_HOLD','JOURNAL_JSON_OR_SCHEMA_HOLD','JOURNAL_EVENT_SCHEMA_HOLD','HASH_CHAIN_HOLD','JOURNAL_HISTORY_REPLAY_HOLD','JOURNAL_BOUND_HOLD','SHADOW_RESERVED','REPLAY_REJECTED','JOURNAL_WRITE_UNCERTAIN_HOLD')

class P8AuditWitnessTests(unittest.TestCase):
    def setUp(self):
        self.f=witness_fixture.RejectionWitnessTests(methodName='test_signed_mapping_matches_but_never_grants_independent_authority');self.f.setUp()
        self.records=[audit_fixture.record(status,500+i) for i,status in enumerate(STATES)]
        self.install(audit.export_bundle(self.records))
    def install(self,document):
        self.f.raw=canonical(document);self.f.mapping.update(snapshot_bytes_sha256=hashlib.sha256(self.f.raw).hexdigest(),record_count=len(document['records']));self.f.resign()
    def document(self):return json.loads(self.f.raw)
    def rehash_invalid(self,document):
        for record in document['records']:record['record_sha256']=audit.digest({k:v for k,v in record.items() if k!='record_sha256'})
        document['export_sha256']=audit.digest({k:v for k,v in document.items() if k!='export_sha256'})
        self.install(document)
    def assert_safe(self,result):
        self.assertEqual(result['decision'],'HOLD')
        for key in ('independent_authority_verified','external_currentness_verified','source_revision_verified','authenticated_audit_storage_verified','durability_verified','complete_history_verified','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(result[key],False)
    def test_complete_thirteen_outcome_bundle_signed_crosswalk_is_still_hold(self):
        result=self.f.call();self.assertTrue(result['mapping_checks_satisfied'],result);self.assert_safe(result)
        REVIEWS.append(dict(case='THIRTEEN_REPORTED_OUTCOMES',record_count=13,actual_journal_executed=False,result=result))
    @unittest.skipUnless(os.name=='nt','Actual complete journal-lock witness integration requires Windows; no lock fallback')
    def test_eight_disposable_cases_reach_existing_witness_verifier(self):
        records=[]
        with tempfile.TemporaryDirectory() as temp:
            def capture(index,kind):
                j=journal.Journal(Path(temp)/str(index));nonce,job='new','new'
                if kind=='input':nonce,job='','j';status=j.transact(nonce,job,'a'*64)
                elif kind=='platform':
                    with patch.object(journal,'msvcrt',None):status=j.transact(nonce,job,'a'*64)
                else:
                    if kind=='json':j.log.write_bytes(b'not-json\n')
                    elif kind=='partial':j.log.write_bytes(b'{')
                    elif kind=='event':
                        e=journal_fixture.event();e['type']='INVENTED';j.log.write_bytes(journal_fixture.raw(journal_fixture.row(e)))
                    elif kind=='replay':self.assertEqual(j.transact(nonce,job,'a'*64),'SHADOW_RESERVED')
                    elif kind=='io':j.log.mkdir()
                    if kind=='fsync':
                        with patch.object(journal.os,'fsync',side_effect=OSError('synthetic fault')):status=j.transact(nonce,job,'a'*64)
                    else:status=j.transact(nonce,job,'a'*64)
                context=dict(attempt_id=f'{1000+index:032x}',operation_id=None,input_digests=dict(job_sha256=None,request_sha256=audit.digest(dict(nonce=nonce,job=job,digest='a'*64)),proposal_sha256=None))
                records.append(audit.record_p8_status(status,context,observed_at=1800000000))
            for index,kind in enumerate(('input','platform','json','partial','event','replay','fsync','io')):capture(index,kind)
        self.install(audit.export_bundle(records));result=self.f.call();self.assertTrue(result['mapping_checks_satisfied'],result);self.assert_safe(result)
        REVIEWS.append(dict(case='EIGHT_DISPOSABLE_JOURNAL_CASES',record_count=8,actual_journal_executed=True,platform_case_simulated=True,fsync_case_injected=True,result=result))
    def test_changed_snapshot_bytes_cannot_reuse_proof(self):
        self.f.raw+=b' ';self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_dropped_record_coherent_export_cannot_reuse_proof(self):
        self.f.raw=canonical(audit.export_bundle(self.records[:-1]));self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_reordered_records_cannot_reuse_proof(self):
        self.f.raw=canonical(audit.export_bundle(list(reversed(self.records))));self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_duplicate_attempt_even_with_fresh_signatures_is_rejected(self):
        d=self.document();d['records'][-1]=copy.deepcopy(d['records'][0]);self.rehash_invalid(d);self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_missing_reason_even_with_fresh_signatures_is_rejected(self):
        d=self.document();del d['records'][0]['reason_code'];self.rehash_invalid(d);self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_unknown_reason_even_with_fresh_signatures_is_rejected(self):
        d=self.document();d['records'][0]['reason_code']='NEW_UNAPPROVED_REASON';self.rehash_invalid(d);self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_permission_claim_even_with_rehashed_records_and_signatures_rejected(self):
        d=self.document();d['records'][0]['may_dispatch']=True;self.rehash_invalid(d);self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_expired_witness_trust_rejects_complete_bundle(self):
        t=self.f.proof['witness_trust'];self.f.proof['witness_trust']=replace(t,expires_utc=self.f.proof['now'].strftime('%Y-%m-%dT%H:%M:%SZ'));self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_wrong_challenge_rejects_complete_bundle(self):
        self.f.proof['expected_challenge']='q'*24;self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_wrong_source_revision_rejects_complete_bundle(self):
        self.f.mapping['source_revision']='b'*40;self.f.resign();self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_shared_key_alias_rejects_complete_bundle(self):
        t=self.f.proof['witness_trust'];keys=dict(t.keys);keys['receipt-role-alias']=next(iter(self.f.proof['receipt_trust'].public_keys.values()));self.f.proof['witness_trust']=replace(t,keys=keys);self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_revoked_signer_rejects_complete_bundle(self):
        t=self.f.proof['witness_trust'];self.f.proof['witness_trust']=replace(t,revoked=frozenset([self.f.proof['witness']['key_id']]));self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_higher_expected_floor_rejects_complete_bundle(self):
        self.f.context['minimum_sequence']=3;self.f.mapping['minimum_sequence']=3;self.f.resign();self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_replay_and_uncertain_reasons_do_not_gain_retry(self):
        d=self.document();reasons={r['reason_code']:r for r in d['records']}
        for reason in ('JOURNAL_REPLAY_QUERY_ONLY','JOURNAL_WRITE_UNCERTAIN_QUERY_ONLY'):
            self.assertFalse(reasons[reason]['automatic_retry']);self.assertEqual(reasons[reason]['transaction_outcome'],'NOT_ATTESTED')
        self.assert_safe(self.f.call())
    def test_repeated_proof_is_not_global_nonce_consumption(self):
        first=self.f.call();self.assertEqual(first,self.f.call());self.assert_safe(first)
    def test_unknown_journal_operation_not_attributed_by_recovery_operation(self):
        self.assertTrue(all(r['operation_id'] is None for r in self.document()['records']));self.assertTrue(self.f.call()['mapping_checks_satisfied']);self.assertFalse(self.f.call()['independent_authority_verified'])
    def test_signed_snapshot_does_not_prove_record_timestamp_freshness(self):
        d=self.document();d['records'][0]['observed_at']=1;self.rehash_invalid(d);r=self.f.call();self.assertTrue(r['mapping_checks_satisfied']);self.assertFalse(r['external_currentness_verified']);self.assertFalse(r['authenticated_audit_storage_verified'])
    def test_missing_external_context_never_uses_signed_mapping_as_context(self):
        self.f.context=None;self.assertFalse(self.f.call()['mapping_checks_satisfied'])
    def test_coherent_change_with_new_fixture_signatures_is_not_live_trust(self):
        d=self.document();d['records'][0]['reason_code']='JOURNAL_IO_HOLD';self.rehash_invalid(d);r=self.f.call();self.assertTrue(r['mapping_checks_satisfied']);self.assert_safe(r)
