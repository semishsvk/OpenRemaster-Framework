"""Independent negative probes; caller selects sealed v015 or candidate v016 module."""
import copy,json,unittest
import test_resource_transaction as fixture
import resource_authority as a
from contextlib import contextmanager

class ResourceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ResourceTransactionTests(methodName='test_atomic_ack_binds_resource_and_reopens');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.ack=self.f.admit();self.store=self.f.store;self.op=self.f.f.binding['operation_id']
    def assert_both_hold(self):
        for action in (lambda:self.store.lookup(self.op),self.store.audit):
            with self.assertRaises(a.Hold):action()
    def test_lower_highwater_holds_lookup_and_audit(self):
        with self.store.connect() as db:db.execute('UPDATE resource_state SET last_sequence=10')
        self.assert_both_hold()
    def test_higher_unexplained_highwater_holds_lookup_and_audit(self):
        with self.store.connect() as db:db.execute('UPDATE resource_state SET last_sequence=99')
        self.assert_both_hold()
    def test_missing_resource_state_holds_lookup_and_audit(self):
        with self.store.connect() as db:db.execute('DELETE FROM resource_state')
        self.assert_both_hold()
    def test_foreign_authority_column_holds(self):
        with self.store.connect() as db:db.execute("UPDATE resource_claims SET authority='FOREIGN'")
        self.assert_both_hold()
    def test_foreign_source_column_holds(self):
        with self.store.connect() as db:db.execute("UPDATE resource_claims SET source='FOREIGN'")
        self.assert_both_hold()
    def test_sequence_column_mismatch_holds(self):
        with self.store.connect() as db:db.execute('UPDATE resource_claims SET sequence=12')
        self.assert_both_hold()
    def test_owner_fence_row_mismatch_holds(self):
        with self.store.connect() as db:db.execute('UPDATE operations SET generation=2')
        self.assert_both_hold()
    def test_owner_epoch_row_mismatch_holds(self):
        with self.store.connect() as db:db.execute('UPDATE operations SET owner_epoch=2')
        self.assert_both_hold()
    def test_policy_epoch_row_mismatch_holds(self):
        with self.store.connect() as db:db.execute('UPDATE operations SET policy_epoch=3')
        self.assert_both_hold()
    def test_extra_orphan_resource_claim_holds_lookup_and_audit(self):
        with self.store.connect() as db:
            db.execute('PRAGMA foreign_keys=OFF')
            db.execute("INSERT INTO resource_claims SELECT 'orphan',authority,source,99,claim_json,claim_sha FROM resource_claims LIMIT 1")
        self.assert_both_hold()
    def test_deleted_resource_claim_holds(self):
        with self.store.connect() as db:db.execute('DELETE FROM resource_claims')
        self.assert_both_hold()
    def test_changed_ack_resource_digest_holds(self):
        ack=copy.deepcopy(self.ack);ack['resource_claim_sha256']='0'*64;ack=self.f.signer({k:v for k,v in ack.items() if k not in ('key_id','signature')})
        with self.store.connect() as db:
            db.execute('UPDATE operations SET ack_json=?',(a.canonical(ack).decode(),));db.execute('UPDATE outbox SET ack_sha=?',(a.digest(a.canonical(ack)),))
        self.assert_both_hold()
    def test_deleted_commit_event_holds_lookup_and_audit(self):
        with self.store.connect() as db:db.execute("DELETE FROM events WHERE kind='LOCAL_ADMISSION_AND_ACK_COMMITTED'")
        self.assert_both_hold()
    def test_duplicate_commit_event_holds_lookup_and_audit(self):
        with self.store.connect() as db:db.execute("INSERT INTO events(kind,operation_id,previous_sha,event_json,event_sha) SELECT kind,operation_id,previous_sha,event_json,event_sha FROM events WHERE kind='LOCAL_ADMISSION_AND_ACK_COMMITTED'")
        self.assert_both_hold()
    def test_unchanged_restart_keeps_exact_ack_query_only(self):
        record=self.f.open().lookup(self.op);self.assertEqual(record['ack'],self.ack);self.assertFalse(record['may_dispatch']);self.assertFalse(record['automatic_retry'])
    def test_audit_and_lookup_use_one_connection_each(self):
        original=self.store.connect;calls=[]
        def counted():calls.append(1);return original()
        self.store.connect=counted
        self.store.lookup(self.op);self.assertEqual(len(calls),1)
        calls.clear();self.store.audit();self.assertEqual(len(calls),1)
    def test_resigned_boolean_ack_epoch_still_rejects(self):
        ack=copy.deepcopy(self.ack);ack['owner_epoch']=True;ack=self.f.signer({k:v for k,v in ack.items() if k not in ('key_id','signature')})
        with self.store.connect() as db:
            db.execute('UPDATE operations SET ack_json=?',(a.canonical(ack).decode(),));db.execute('UPDATE outbox SET ack_sha=?',(a.digest(a.canonical(ack)),))
        self.assert_both_hold()
    def test_rehashed_commit_event_wrong_resource_binding_holds(self):
        with self.store.connect() as db:
            row=db.execute("SELECT sequence,event_json FROM events WHERE kind='LOCAL_ADMISSION_AND_ACK_COMMITTED'").fetchone()
            event=json.loads(row['event_json']);event['details']['resource_claim_sha256']='0'*64
            db.execute('UPDATE events SET event_json=?,event_sha=? WHERE sequence=?',(a.canonical(event).decode(),a.digest(a.canonical(event)),row['sequence']))
        self.assert_both_hold()
    def test_consistent_unknown_lookup_is_hold_not_admission(self):
        r=self.store.lookup('unknown');self.assertEqual(r['status'],'UNKNOWN_HOLD');self.assertFalse(r['may_dispatch']);self.assertFalse(r['automatic_retry'])
    def test_concurrent_commit_cannot_mix_lookup_snapshots(self):
        original=self.store.connect;changed=[]
        @contextmanager
        def instrumented():
            with original() as db:
                def trace(sql):
                    if 'SELECT fence,policy,last_sequence FROM resource_state' in sql and not changed:
                        with original() as writer:writer.execute('UPDATE resource_state SET last_sequence=99')
                        changed.append(True)
                db.set_trace_callback(trace);yield db
        self.store.connect=instrumented
        record=self.store.lookup(self.op)
        self.assertEqual(changed,[True]);self.assertEqual(record['ack'],self.ack)
        self.store.connect=original
        with self.assertRaises(a.Hold):self.store.lookup(self.op)
    def test_oversized_or_deep_claim_is_structured_hold(self):
        for raw in ('x'*33000,'['*2000+'0'+']'*2000):
            with self.store.connect() as db:db.execute('UPDATE resource_claims SET claim_json=?',(raw,))
            self.assert_both_hold()
