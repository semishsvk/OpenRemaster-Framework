"""Negative-first validation of a copied Windows-only shadow journal."""
import copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import p8_journal as p8

def row(event,previous='0'*64):
    return dict(prev=previous,event=event,hash=hashlib.sha256((previous+json.dumps(event,sort_keys=True,separators=(',',':'))).encode()).hexdigest())
def event(seq=1,nonce='n',job='j'):return dict(seq=seq,nonce=nonce,job=job,digest='a'*64,type='RESERVE')
def raw(row):return (json.dumps(row)+'\n').encode()

class P8ParserTests(unittest.TestCase):
    def reject(self,value,code):
        with self.assertRaisesRegex(p8.JournalInvalid,code):p8.validate_journal(value)
    def test_valid_legacy_row_keeps_exact_fields(self):self.assertEqual(p8.validate_journal(raw(row(event()))),[event()])
    def test_empty_log_is_valid(self):self.assertEqual(p8.validate_journal(b''),[])
    def test_partial_tail_rejected(self):self.reject(b'{"event":','PARTIAL_JOURNAL_HOLD')
    def test_malformed_json_is_structured_hold(self):
        for value in (b'not-json\n',b'\xff\n',b'[]\n',b'null\n',b'\n'):self.reject(value,'JOURNAL_JSON_OR_SCHEMA_HOLD')
    def test_duplicate_keys_and_nonfinite_values_rejected(self):
        value=raw(row(event())).rstrip(b'\n')[:-1]+b',"prev":"'+b'0'*64+b'"}\n';self.reject(value,'JOURNAL_JSON_OR_SCHEMA_HOLD')
        self.reject(b'{"x":NaN}\n','JOURNAL_JSON_OR_SCHEMA_HOLD')
    def test_unknown_or_extra_event_fields_rejected(self):
        for key,value in [('type','INVENTED'),('digest','bad'),('nonce',''),('job','../escape'),('extra',True)]:
            e=event();e[key]=value;self.reject(raw(row(e)),'JOURNAL_EVENT_SCHEMA_HOLD')
    def test_sequence_requires_exact_integer_order(self):
        for seq in (True,1.0,0,2,-1,'1'):self.reject(raw(row(event(seq=seq))),'JOURNAL_EVENT_SCHEMA_HOLD')
    def test_hash_mismatch_rejected(self):
        r=row(event());r['hash']='f'*64;self.reject(raw(r),'HASH_CHAIN_HOLD')
    def test_history_replay_rejected_even_with_recomputed_chain(self):
        first=row(event());second=row(event(seq=2),first['hash']);self.reject(raw(first)+raw(second),'JOURNAL_HISTORY_REPLAY_HOLD')
    def test_total_size_and_record_bounds(self):
        self.reject(b'x'*(p8.MAX_BYTES+1),'JOURNAL_BOUND_HOLD')
        self.reject(b'{}\n'*(p8.MAX_RECORDS+1),'JOURNAL_BOUND_HOLD')
    def test_valid_recomputed_chain_is_not_authentication(self):
        e=event();e['digest']='f'*64;self.assertEqual(p8.validate_journal(raw(row(e))),[e])

@unittest.skipUnless(os.name=='nt','Real P8 msvcrt byte-lock execution requires Windows; no fallback lock is substituted')
class P8WindowsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.j=p8.Journal(self.temp.name)
    def call(self):return self.j.transact('new','new','a'*64)
    def test_normal_and_duplicate_semantics_preserved(self):
        self.assertEqual(self.call(),'SHADOW_RESERVED');self.assertEqual(self.call(),'REPLAY_REJECTED')
    def test_malformed_json_does_not_append(self):
        self.j.log.write_bytes(b'not-json\n');before=self.j.log.read_bytes();self.assertEqual(self.call(),'JOURNAL_JSON_OR_SCHEMA_HOLD');self.assertEqual(self.j.log.read_bytes(),before)
    def test_unknown_event_does_not_append(self):
        e=event();e['type']='INVENTED';before=raw(row(e));self.j.log.write_bytes(before);self.assertEqual(self.call(),'JOURNAL_EVENT_SCHEMA_HOLD');self.assertEqual(self.j.log.read_bytes(),before)
    def test_invalid_inputs_never_create_log(self):
        for nonce,job,digest in [('', 'j','a'*64),('n','','a'*64),('n','j','bad'),(True,'j','a'*64),('n','../j','a'*64),('n'*129,'j','a'*64)]:
            self.assertEqual(self.j.transact(nonce,job,digest),'INPUT_SCHEMA_HOLD');self.assertFalse(self.j.log.exists())
    def test_partial_tail_preserved(self):
        self.j.log.write_bytes(b'{');self.assertEqual(self.call(),'PARTIAL_JOURNAL_HOLD');self.assertEqual(self.j.log.read_bytes(),b'{')
    def test_hash_mismatch_preserved(self):
        r=row(event());r['hash']='f'*64;self.j.log.write_bytes(raw(r));self.assertEqual(self.call(),'HASH_CHAIN_HOLD')
    def test_duplicate_json_keys_hold(self):
        r=raw(row(event())).rstrip(b'\n')[:-1]+b',"prev":"'+b'0'*64+b'"}\n';self.j.log.write_bytes(r);self.assertEqual(self.call(),'JOURNAL_JSON_OR_SCHEMA_HOLD')
    def test_nonfinite_hold(self):
        self.j.log.write_bytes(b'{"x":NaN}\n');self.assertEqual(self.call(),'JOURNAL_JSON_OR_SCHEMA_HOLD')
    def test_nonsequential_event_hold(self):
        self.j.log.write_bytes(raw(row(event(seq=900))));self.assertEqual(self.call(),'JOURNAL_EVENT_SCHEMA_HOLD')
    def test_repeated_historical_nonce_hold(self):
        r=row(event());self.j.log.write_bytes(raw(r)+raw(row(event(seq=2),r['hash'])));self.assertEqual(self.call(),'JOURNAL_HISTORY_REPLAY_HOLD')
    def test_oversized_log_hold_without_append(self):
        self.j.log.write_bytes(b'x'*(1024*1024+1));before=self.j.log.stat().st_size;self.assertEqual(self.call(),'JOURNAL_BOUND_HOLD');self.assertEqual(self.j.log.stat().st_size,before)
    def test_two_real_processes_commit_once(self):
        code="import sys;sys.path.insert(0,sys.argv[1]);from p8_journal import Journal;print(Journal(sys.argv[2]).transact('same','same','a'*64))"
        command=[sys.executable,'-B','-c',code,str(Path(p8.__file__).parent),self.temp.name]
        children=[subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
        try:
            results=[]
            for child in children:
                stdout,stderr=child.communicate(timeout=10);self.assertEqual(child.returncode,0,stderr);results.append(stdout.strip())
            self.assertEqual(sorted(results),['REPLAY_REJECTED','SHADOW_RESERVED'])
        finally:
            for child in children:
                if child.poll() is None:child.kill();child.communicate(timeout=5)
    def test_fsync_failure_is_uncertain_hold_not_retry(self):
        with patch.object(p8.os,'fsync',side_effect=OSError('synthetic fsync failure')):self.assertEqual(self.call(),'JOURNAL_WRITE_UNCERTAIN_HOLD')
        self.assertEqual(self.call(),'REPLAY_REJECTED')
    def test_read_io_failure_is_structured_hold(self):
        self.j.log.mkdir();self.assertEqual(self.call(),'JOURNAL_IO_HOLD')
    def test_coherent_valid_rewrite_remains_explicitly_unauthenticated(self):
        e=event();e['digest']='f'*64;self.j.log.write_bytes(raw(row(e)))
        self.assertEqual(self.call(),'SHADOW_RESERVED')  # Integrity only; production remains HOLD.

class P8PlatformGuardTests(unittest.TestCase):
    def test_missing_windows_lock_never_uses_fallback(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(p8,'msvcrt',None):
            j=p8.Journal(temp);self.assertEqual(j.transact('n','j','a'*64),'WINDOWS_LOCK_UNAVAILABLE_HOLD');self.assertFalse(j.log.exists())
