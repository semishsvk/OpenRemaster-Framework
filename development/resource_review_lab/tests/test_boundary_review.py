import hashlib,unittest
from boundary_review import review_dev_boundary

class BoundaryReviewTests(unittest.TestCase):
    def review(self,source):return review_dev_boundary(source,expected_sha256=hashlib.sha256(source).hexdigest())
    def test_pinned_declared_route_remains_hold(self):
        r=self.review(b"SCENARIOS={'build_studio_dev'}\ndef dispatch(req):\n return submit(req)\n")
        self.assertEqual(r['syntax']['literal_set_constants']['SCENARIOS'],['build_studio_dev'])
        self.assertEqual(r['syntax']['functions']['dispatch']['direct_call_syntax'][0]['target'],'submit')
        self.assertEqual(r['decision'],'HOLD')
        for k in ('independent_admission_verified','owner_lease_verified','resource_authority_verified','k003_compatibility_verified','worker_liveness_verified','source_executed','dispatch_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[k],False)
    def test_drift_never_parsed_as_verified_source(self):
        r=review_dev_boundary(b'def dispatch(): pass',expected_sha256='0'*64);self.assertEqual(r['reason'],'SOURCE_DRIFT');self.assertIsNone(r['syntax'])
    def test_missing_or_invalid_pin_holds(self):
        for value in (None,'a'*63,'A'*64,True):self.assertEqual(review_dev_boundary(b'pass',expected_sha256=value)['reason'],'SOURCE_PIN_REQUIRED')
    def test_comments_strings_and_metadata_cannot_become_authority(self):
        r=self.review(b"# verify_admission(req)\nmetadata='owner_verified=True; verify_signature()'\ntrust_class='SECURE_PRODUCTION'\ndef dispatch(req):\n return submit(req)\n")
        self.assertEqual([x['target'] for x in r['syntax']['functions']['dispatch']['direct_call_syntax']],['submit'])
        self.assertFalse(r['independent_admission_verified']);self.assertFalse(r['production_go'])
    def test_named_check_is_syntax_not_trust(self):
        r=self.review(b'def dispatch(req):\n verify_admission(req)\n return submit(req)\n')
        self.assertIn('verify_admission',[x['target'] for x in r['syntax']['functions']['dispatch']['direct_call_syntax']]);self.assertFalse(r['independent_admission_verified'])
    def test_malicious_top_level_source_is_never_executed(self):
        r=self.review(b"raise RuntimeError('MUST_NOT_EXECUTE')\n__import__('os').system('MUST_NOT_EXECUTE')\ndef dispatch(req): pass\n")
        self.assertFalse(r['source_executed']);self.assertIsNotNone(r['syntax'])
    def test_duplicate_definition_holds_instead_of_hiding_override(self):
        r=self.review(b'def dispatch(req): verify_admission(req)\ndef dispatch(req): submit(req)\n');self.assertEqual(r['reason'],'DUPLICATE_FUNCTION_DECLARATION')
    def test_invalid_encoding_or_syntax_is_structured_hold(self):
        for source in (b'\xff',b'def broken(',b'\0'):
            self.assertEqual(self.review(source)['reason'],'SOURCE_PARSE_HOLD')
    def test_bounded_bytes_only(self):
        for source in ('pass',b'',b' '*262145):self.assertEqual(review_dev_boundary(source,expected_sha256='a'*64)['reason'],'SOURCE_BOUND_OR_TYPE')
    def test_request_literals_are_observed_without_evaluating_them(self):
        r=self.review(b"def validate(req):\n allowed={'action','operation_id','scenario'}\n return req\n")
        self.assertEqual(r['syntax']['functions']['validate']['literal_string_sets'],[['action','operation_id','scenario']])
