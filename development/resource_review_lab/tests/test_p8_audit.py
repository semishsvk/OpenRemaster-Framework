"""Exercise copied journal -> existing boundary -> existing export/import."""
import hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from admission_boundary_base import canonical
import rejection_evidence as audit
from rejection_import import review_import
import p8_journal as journal

RECORDS=[]
def context(attempt=1):return dict(attempt_id=f'{attempt:032x}',operation_id=None,input_digests=dict(job_sha256=None,request_sha256=audit.digest(dict(nonce='new',job='new',digest='a'*64)),proposal_sha256=None))
def record(status,attempt=1):return audit.record_p8_status(status,context(attempt),observed_at=1800000000)

class P8ReasonTests(unittest.TestCase):
    def test_p8_known_reason_not_downgraded(self):
        r=audit.rejection_record(dict(decision='HOLD',reason='JOURNAL_EVENT_SCHEMA_HOLD'),context(),observed_at=1);self.assertEqual(r['reason_code'],'JOURNAL_EVENT_SCHEMA_HOLD')
    def test_all_p8_codes_keep_vetted_reason(self):
        states={'INPUT_SCHEMA_HOLD':'INPUT_SCHEMA_HOLD','WINDOWS_LOCK_UNAVAILABLE_HOLD':'WINDOWS_LOCK_UNAVAILABLE_HOLD','JOURNAL_IO_HOLD':'JOURNAL_IO_HOLD','LOCK_TIMEOUT_HOLD':'LOCK_TIMEOUT_HOLD','PARTIAL_JOURNAL_HOLD':'PARTIAL_JOURNAL_HOLD','JOURNAL_JSON_OR_SCHEMA_HOLD':'JOURNAL_JSON_OR_SCHEMA_HOLD','JOURNAL_EVENT_SCHEMA_HOLD':'JOURNAL_EVENT_SCHEMA_HOLD','HASH_CHAIN_HOLD':'HASH_CHAIN_HOLD','JOURNAL_HISTORY_REPLAY_HOLD':'JOURNAL_HISTORY_REPLAY_HOLD','JOURNAL_BOUND_HOLD':'JOURNAL_BOUND_HOLD','SHADOW_RESERVED':'SHADOW_RESERVATION_NOT_AUTHORITY','REPLAY_REJECTED':'JOURNAL_REPLAY_QUERY_ONLY','JOURNAL_WRITE_UNCERTAIN_HOLD':'JOURNAL_WRITE_UNCERTAIN_QUERY_ONLY'}
        for state,reason in states.items():
            with self.subTest(state=state):self.assertEqual(record(state)['reason_code'],reason)
    def test_unknown_text_never_exports_paths_or_claimed_status(self):
        r=record('C:/private/secret UNKNOWN_HOLD');self.assertEqual(r['reason_code'],'UNRECOGNIZED_JOURNAL_STATUS');self.assertNotIn('private',json.dumps(r))
    def test_forged_precomputed_result_cannot_grant_authority(self):
        r=record(dict(status='PASS',may_dispatch=True));self.assertEqual(r['decision'],'HOLD');self.assertFalse(r['may_dispatch'])
    def test_existing_snapshot_import_matches_without_trust(self):
        raw=canonical(audit.export_bundle([record('HASH_CHAIN_HOLD')]));r=review_import(raw,expected_bytes_sha256=hashlib.sha256(raw).hexdigest(),expected_record_count=1);self.assertTrue(r['integrity_matched']);self.assertFalse(r['authenticated']);self.assertEqual(r['decision'],'HOLD')
    def test_modified_snapshot_rejected(self):
        raw=canonical(audit.export_bundle([record('HASH_CHAIN_HOLD')]));self.assertFalse(review_import(raw+b' ',expected_bytes_sha256=hashlib.sha256(raw).hexdigest(),expected_record_count=1)['integrity_matched'])
    def test_invalid_attempt_context_rejected(self):
        with self.assertRaises(ValueError):audit.record_p8_status('INPUT_SCHEMA_HOLD',dict(context(),attempt_id='../bad'),observed_at=1)
    def test_query_only_reason_never_requests_retry(self):
        for state in ('REPLAY_REJECTED','JOURNAL_WRITE_UNCERTAIN_HOLD'):
            r=record(state);self.assertTrue(r['reason_code'].endswith('QUERY_ONLY'));self.assertFalse(r['automatic_retry']);self.assertEqual(r['transaction_outcome'],'NOT_ATTESTED')
    def test_duplicate_attempt_still_rejected(self):
        r=record('HASH_CHAIN_HOLD')
        with self.assertRaises(ValueError):audit.export_bundle([r,r])
    def test_unknown_generic_reason_still_normalized(self):
        r=audit.rejection_record(dict(decision='REJECT',reason='arbitrary detail'),context(),observed_at=1);self.assertEqual(r['reason_code'],'UNCLASSIFIED_FAILURE')

class PortableJournalAuditTests(unittest.TestCase):
    def capture(self,status,attempt):
        r=record(status,attempt);RECORDS.append(r)
        bundle=audit.export_bundle([r]);raw=canonical(bundle)
        self.assertTrue(review_import(raw,expected_bytes_sha256=hashlib.sha256(raw).hexdigest(),expected_record_count=1)['integrity_matched'])
        self.assertFalse(r['may_dispatch']);self.assertFalse(r['automatic_retry']);return r
    def test_actual_invalid_input_has_no_log_and_exports(self):
        with tempfile.TemporaryDirectory() as temp:
            j=journal.Journal(temp);status=j.transact('','j','a'*64);r=self.capture(status,101);self.assertEqual(r['reason_code'],'INPUT_SCHEMA_HOLD');self.assertFalse(j.log.exists())
    def test_missing_platform_branch_is_reported_only(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(journal,'msvcrt',None):
            j=journal.Journal(temp);r=self.capture(j.transact('n','j','a'*64),102);self.assertEqual(r['reason_code'],'WINDOWS_LOCK_UNAVAILABLE_HOLD');self.assertFalse(j.log.exists())

@unittest.skipUnless(os.name=='nt','Actual journal-lock audit integration requires Windows, no substitute lock')
class WindowsJournalAuditTests(PortableJournalAuditTests):
    # Keep inherited portable cases out of this class to avoid duplicate capture.
    test_actual_invalid_input_has_no_log_and_exports=None
    test_missing_platform_branch_is_reported_only=None
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.j=journal.Journal(self.temp.name)
    def transact(self):return self.j.transact('new','new','a'*64)
    def test_malformed_json_roundtrip_without_append(self):
        before=b'not-json\n';self.j.log.write_bytes(before);r=self.capture(self.transact(),103);self.assertEqual(r['reason_code'],'JOURNAL_JSON_OR_SCHEMA_HOLD');self.assertEqual(self.j.log.read_bytes(),before)
    def test_partial_tail_roundtrip_without_append(self):
        self.j.log.write_bytes(b'{');r=self.capture(self.transact(),104);self.assertEqual(r['reason_code'],'PARTIAL_JOURNAL_HOLD');self.assertEqual(self.j.log.read_bytes(),b'{')
    def test_unknown_event_roundtrip_without_append(self):
        e=dict(seq=1,nonce='n',job='j',digest='a'*64,type='INVENTED');previous='0'*64;row=dict(prev=previous,event=e,hash=hashlib.sha256((previous+json.dumps(e,sort_keys=True,separators=(',',':'))).encode()).hexdigest());before=(json.dumps(row)+'\n').encode();self.j.log.write_bytes(before)
        r=self.capture(self.transact(),105);self.assertEqual(r['reason_code'],'JOURNAL_EVENT_SCHEMA_HOLD');self.assertEqual(self.j.log.read_bytes(),before)
    def test_replay_roundtrip_is_query_only(self):
        self.assertEqual(self.transact(),'SHADOW_RESERVED');before=self.j.log.read_bytes();r=self.capture(self.transact(),106);self.assertEqual(r['reason_code'],'JOURNAL_REPLAY_QUERY_ONLY');self.assertEqual(self.j.log.read_bytes(),before)
    def test_uncertain_fsync_roundtrip_never_reexecutes(self):
        with patch.object(journal.os,'fsync',side_effect=OSError('synthetic fault')):status=self.transact()
        before=self.j.log.read_bytes();r=self.capture(status,107);self.assertEqual(r['reason_code'],'JOURNAL_WRITE_UNCERTAIN_QUERY_ONLY');self.assertEqual(self.j.log.read_bytes(),before);self.assertEqual(len(before.splitlines()),1)
    def test_io_hold_roundtrip(self):
        self.j.log.mkdir();r=self.capture(self.transact(),108);self.assertEqual(r['reason_code'],'JOURNAL_IO_HOLD');self.assertTrue(self.j.log.is_dir())
