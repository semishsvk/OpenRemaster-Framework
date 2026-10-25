import copy,unittest
import p8_failclosed as boundary

FLAGS=('may_enqueue','may_dispatch','may_start_worker','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_authority','dispatch_authorized','worker_execution_authorized','independent_authority_verified','release_eligible','production_go')
class Fake:
    def __init__(self,value):self.value=value
    def observe(self,now):return self.value

class ExistingBoundaryTests(unittest.TestCase):
    def base(self):return dict(status='READONLY_OBSERVATION_VALIDATED_NOT_AUTHORITY',may_dispatch=False,may_start_worker=False)
    def test_legacy_readonly_status_preserved(self):self.assertEqual(boundary.observe_safely(Fake(self.base()))['status'],'READONLY_OBSERVATION_VALIDATED_NOT_AUTHORITY')
    def test_original_dispatch_denial_preserved(self):
        r=boundary.observe_safely(Fake(dict(self.base(),may_dispatch=True)));self.assertEqual(r['status'],'HOLD_NO_AUTO_RETRY');self.assertFalse(r['may_dispatch'])
    def test_explicit_enqueue_claim_is_hold(self):
        r=boundary.observe_safely(Fake(dict(self.base(),may_enqueue=True)));self.assertEqual(r['status'],'HOLD_NO_AUTO_RETRY');self.assertIs(r['may_enqueue'],False)
    def test_retry_claim_is_hold(self):
        r=boundary.observe_safely(Fake(dict(self.base(),automatic_retry=True)));self.assertEqual(r['status'],'HOLD_NO_AUTO_RETRY');self.assertIs(r['automatic_retry'],False)
    def test_other_capabilities_cannot_leak(self):
        for flag in FLAGS:
            with self.subTest(flag=flag):
                r=boundary.observe_safely(Fake(dict(self.base(),**{flag:True})));self.assertEqual(r['status'],'HOLD_NO_AUTO_RETRY');self.assertIs(r[flag],False)
    def test_missing_legacy_flags_are_disabled(self):
        r=boundary.observe_safely(Fake(self.base()))
        for flag in FLAGS:self.assertIs(r[flag],False)

class JournalOutcomeTests(unittest.TestCase):
    def assert_safe(self,r):
        self.assertEqual(r['status'],'HOLD_NO_AUTO_RETRY')
        for flag in FLAGS:self.assertIs(r[flag],False)
    def test_every_journal_hold_is_no_retry_and_no_queue(self):
        states=('INPUT_SCHEMA_HOLD','WINDOWS_LOCK_UNAVAILABLE_HOLD','JOURNAL_IO_HOLD','LOCK_TIMEOUT_HOLD','PARTIAL_JOURNAL_HOLD','JOURNAL_JSON_OR_SCHEMA_HOLD','JOURNAL_EVENT_SCHEMA_HOLD','HASH_CHAIN_HOLD','JOURNAL_HISTORY_REPLAY_HOLD','JOURNAL_BOUND_HOLD')
        for state in states:
            with self.subTest(state=state):
                r=boundary.observe_journal_status(state);self.assert_safe(r);self.assertEqual(r['reason_code'],state)
    def test_shadow_reserved_never_turns_into_enqueue(self):
        r=boundary.observe_journal_status('SHADOW_RESERVED');self.assert_safe(r);self.assertEqual(r['reason_code'],'SHADOW_RESERVATION_NOT_AUTHORITY')
    def test_uncertain_write_is_query_only(self):
        r=boundary.observe_journal_status('JOURNAL_WRITE_UNCERTAIN_HOLD');self.assert_safe(r);self.assertTrue(r['query_only']);self.assertFalse(r['query_performed'])
    def test_replay_never_resubmits(self):
        r=boundary.observe_journal_status('REPLAY_REJECTED');self.assert_safe(r);self.assertTrue(r['query_only'])
    def test_unknown_result_does_not_use_truthiness_or_hold_suffix(self):
        for state in ('QUEUED','SIGNED','UNKNOWN_HOLD','SHADOW_COMMITTED','SHADOW_RESERVED ','x'*10000,True,{},None):
            self.assert_safe(boundary.observe_journal_status(state))
    def test_unknown_capability_field_is_not_forwarded(self):
        r=boundary.observe_safely(Fake(dict(status='READONLY_OBSERVATION_VALIDATED_NOT_AUTHORITY',may_dispatch=False,may_start_worker=False,may_execute=True)));self.assert_safe(r);self.assertNotIn('may_execute',r)
    def test_provider_exception_is_hold_without_retry(self):
        class Broken:
            def observe(self,now):raise OSError('synthetic')
        self.assert_safe(boundary.observe_safely(Broken()))
    def test_flags_require_exact_false(self):
        for value in (0,None,'false',[],True):
            r=boundary.observe_safely(Fake(dict(status='READONLY_OBSERVATION_VALIDATED_NOT_AUTHORITY',may_dispatch=False,may_start_worker=False,may_enqueue=value)));self.assert_safe(r)
    def test_inputs_not_mutated(self):
        source=dict(status='READONLY_OBSERVATION_VALIDATED_NOT_AUTHORITY',may_dispatch=False,may_start_worker=False);before=copy.deepcopy(source);boundary.observe_safely(Fake(source));self.assertEqual(source,before)
