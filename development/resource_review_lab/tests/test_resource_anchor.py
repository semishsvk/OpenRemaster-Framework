import copy,hashlib,hmac,secrets,sqlite3,unittest
from contextlib import closing
from pathlib import Path
import test_resource_transaction as fixture
from resource_anchor import capture_resource_state,review_resource_anchor
from anchor import canonical
from scope import Hold

class ResourceAnchorTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ResourceTransactionTests(methodName='test_atomic_ack_binds_resource_and_reopens');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.store=self.f.store;self.old=Path(self.f.temp.name)/'old.sqlite3'
        with self.store.connect() as source,closing(sqlite3.connect(self.old)) as target:source.backup(target)
        self.ack=self.f.admit();self.key=secrets.token_bytes(32)
        self.expected=dict(authority_id='synthetic-witness',scope_id='synthetic-resource-scope',ledger_id='synthetic-ledger',challenge='synthetic-challenge-123',min_sequence=2)
        self.current=self.sign();self.presented=copy.deepcopy(self.current);self.calls=0
    def state(self):return capture_resource_state(self.store,ledger_id=self.expected['ledger_id'],scope_id=self.expected['scope_id'])
    def sign(self,**changes):
        body=dict(schema='OpenRemaster.ResourceLedgerAnchor.v1',authority_id=self.expected['authority_id'],scope_id=self.expected['scope_id'],ledger_id=self.expected['ledger_id'],challenge=self.expected['challenge'],sequence=2,state_sha256=hashlib.sha256(canonical(self.state())).hexdigest(),issued_at=self.f.f.now-1,expires_at=self.f.f.now+10,key_id='ephemeral-witness')
        body.update(changes);body['signature']=hmac.new(self.key,canonical(body),hashlib.sha256).hexdigest();return body
    def provider(self):self.calls+=1;return copy.deepcopy(self.current)
    def verify(self,doc):
        signature=doc.get('signature');body={k:v for k,v in doc.items() if k!='signature'}
        return type(signature) is str and hmac.compare_digest(signature,hmac.new(self.key,canonical(body),hashlib.sha256).hexdigest())
    def call(self,**kw):
        args=dict(expected=self.expected,trusted_current=self.provider,verifier=self.verify,now=self.f.f.now);args.update(kw)
        return review_resource_anchor(self.store,self.presented,**args)
    def restore(self):
        with closing(sqlite3.connect(self.old)) as source,self.store.connect() as target:source.backup(target)
    def test_matching_anchor_still_shadow_hold(self):
        r=self.call();self.assertTrue(r['anchor_checks_satisfied']);self.assertEqual(r['decision'],'HOLD');self.assertEqual(self.calls,1)
        for k in ('independent_authority_verified','live_freshness_verified','dispatch_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[k],False)
    def test_coherent_entire_database_rollback_detected_by_separate_current(self):
        self.restore();self.assertEqual(self.store.audit()['operations'],0)
        r=self.call();self.assertFalse(r['anchor_checks_satisfied']);self.assertEqual(r['reason'],'LOCAL_ROLLBACK_OR_DRIFT')
    def test_old_presented_anchor_rejected_against_current(self):
        self.presented=self.sign(sequence=1);self.expected['min_sequence']=1
        self.assertEqual(self.call()['reason'],'STALE_OR_FORGED_ANCHOR')
    def test_replayed_current_below_independent_sequence_floor_holds(self):
        self.current=self.sign(sequence=1);self.presented=copy.deepcopy(self.current)
        self.assertEqual(self.call()['reason'],'RESOURCE_ANCHOR_SEQUENCE_HOLD')
    def test_local_state_changed_after_anchor(self):
        with self.store.connect() as db:db.execute('UPDATE resource_state SET fence=4')
        self.assertEqual(self.call()['reason'],'LOCAL_ROLLBACK_OR_DRIFT')
    def test_schema_drift_is_in_snapshot_digest(self):
        with self.store.connect() as db:db.execute('CREATE TABLE injected_schema(x)')
        self.assertEqual(self.call()['reason'],'LOCAL_ROLLBACK_OR_DRIFT')
    def test_foreign_scope_ledger_authority_or_challenge_holds(self):
        for key in ('scope_id','ledger_id','authority_id','challenge'):
            self.presented=self.sign(**{key:'FOREIGN'});self.assertEqual(self.call()['reason'],'RESOURCE_ANCHOR_SCOPE_MISMATCH')
    def test_expired_and_future_anchor_holds(self):
        for values in [dict(expires_at=self.f.f.now),dict(issued_at=self.f.f.now+1),dict(expires_at=self.f.f.now+40)]:
            self.presented=self.sign(**values);self.assertEqual(self.call()['reason'],'RESOURCE_ANCHOR_EXPIRED_OR_FUTURE')
    def test_forged_signature_holds(self):
        self.current['signature']='0'*64;self.presented=copy.deepcopy(self.current)
        self.assertEqual(self.call()['reason'],'UNTRUSTED_CURRENT_ANCHOR')
    def test_no_provider_or_verifier_holds(self):
        self.assertEqual(self.call(trusted_current=None)['reason'],'NO_INDEPENDENT_AUTHORITY')
        self.assertEqual(self.call(verifier=None)['reason'],'NO_INDEPENDENT_AUTHORITY')
    def test_truthy_non_boolean_verifier_is_not_accepted(self):
        for value in (1,'verified',{'verified':True}):self.assertEqual(self.call(verifier=lambda doc:value)['reason'],'UNTRUSTED_CURRENT_ANCHOR')
    def test_provider_exception_is_hold_without_retry(self):
        calls=[]
        def broken():calls.append(1);raise OSError('synthetic unavailable')
        r=self.call(trusted_current=broken);self.assertEqual(r['reason'],'RESOURCE_ANCHOR_PROVIDER_OR_VERIFIER_UNCERTAIN');self.assertEqual(calls,[1])
    def test_changed_provider_return_cannot_mutate_frozen_anchor(self):
        def mutating(doc):doc['sequence']=99;return False
        before=copy.deepcopy(self.current);self.assertFalse(self.call(verifier=mutating)['anchor_checks_satisfied']);self.assertEqual(self.current,before)
    def test_invalid_sequence_clock_or_schema_holds(self):
        for sequence in (True,0,-1):
            self.presented=self.sign(sequence=sequence);self.assertEqual(self.call()['reason'],'RESOURCE_ANCHOR_SEQUENCE_HOLD')
        self.presented=copy.deepcopy(self.current)
        for clock in (None,True,-1):self.assertEqual(self.call(now=clock)['reason'],'VERIFIED_CLOCK_REQUIRED')
        self.presented['production_go']=True;self.assertEqual(self.call()['reason'],'RESOURCE_ANCHOR_SCHEMA')
    def test_snapshot_is_deterministic_read_only_and_detached(self):
        before=self.state();again=self.state();self.assertEqual(before,again)
        before['tables']['operations'].clear();self.assertEqual(self.state(),again)
    def test_reopening_database_preserves_anchor_match(self):
        self.store=self.f.open();self.assertTrue(self.call()['anchor_checks_satisfied'])
    def test_resource_corruption_holds_before_anchor_comparison(self):
        with self.store.connect() as db:db.execute('UPDATE resource_state SET last_sequence=99')
        self.assertFalse(self.call()['anchor_checks_satisfied'])
    def test_missing_snapshot_database_is_not_created(self):
        missing=Path(self.f.temp.name)/'does-not-exist.sqlite3';store=copy.copy(self.store);store.dbpath=missing
        with self.assertRaises(Hold):capture_resource_state(store,ledger_id='synthetic-ledger',scope_id='synthetic-scope')
        self.assertFalse(missing.exists())
