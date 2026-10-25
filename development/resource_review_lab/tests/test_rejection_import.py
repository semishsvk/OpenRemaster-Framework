import copy,hashlib,json,unittest
from admission_boundary_base import canonical
from rejection_evidence import rejection_record,export_bundle,digest
from rejection_import import review_import,MAX_BYTES

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.records=[rejection_record(dict(decision='HOLD',reason='STALE_OWNER_LEASE'),dict(attempt_id=f'{i:032x}',operation_id=None,input_digests=dict(job_sha256=None,request_sha256=None,proposal_sha256=None)),observed_at=1800000000) for i in (1,2)]
        self.bundle=export_bundle(self.records);self.raw=canonical(self.bundle);self.expected=hashlib.sha256(self.raw).hexdigest()
    def call(self,raw=None,expected=None,count=2):return review_import(self.raw if raw is None else raw,expected_bytes_sha256=self.expected if expected is None else expected,expected_record_count=count)
    def repinned(self,raw,count=2):return self.call(raw,hashlib.sha256(raw).hexdigest(),count)
    def test_valid_integrity_never_grants_authenticity_or_execution(self):
        r=self.call();self.assertTrue(r['integrity_matched']);self.assertEqual(r['decision'],'HOLD')
        for key in ('expected_digest_authority_verified','independent_authority_verified','authenticated','durability_verified','complete_history_verified','freshness_verified','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[key],False)
    def test_missing_expected_digest_holds(self):self.assertEqual(review_import(self.raw,expected_record_count=2)['decision'],'HOLD')
    def test_invalid_expected_counts_hold(self):
        for count in (None,True,0,129,2.0,'2'):
            with self.subTest(count=count):self.assertEqual(self.call(count=count)['decision'],'HOLD')
    def test_exact_bytes_not_only_semantic_json(self):
        pretty=json.dumps(self.bundle,indent=2).encode();self.assertFalse(self.call(pretty)['integrity_matched']);self.assertTrue(self.repinned(pretty)['integrity_matched'])
    def test_reordered_records_reject_against_expected_snapshot(self):self.assertEqual(self.call(canonical(export_bundle(list(reversed(self.records)))))['reason'],'EXPECTED_BYTES_DIGEST_MISMATCH')
    def test_deleted_record_coherent_rehash_still_rejects(self):self.assertFalse(self.call(canonical(export_bundle(self.records[:1])))['integrity_matched'])
    def test_coherent_rewrite_rejects_against_external_expected_hash(self):
        records=copy.deepcopy(self.records);records[0]['observed_at']+=1;records[0]['record_sha256']=digest({k:v for k,v in records[0].items() if k!='record_sha256'})
        self.assertFalse(self.call(canonical(export_bundle(records)))['integrity_matched'])
    def test_changed_expectation_is_not_independent_trust(self):
        raw=canonical(export_bundle(list(reversed(self.records))));r=self.repinned(raw);self.assertTrue(r['integrity_matched']);self.assertFalse(r['expected_digest_authority_verified']);self.assertEqual(r['decision'],'HOLD')
    def test_truncated_bytes_reject_even_if_repinned(self):self.assertEqual(self.repinned(self.raw[:-1])['decision'],'REJECT')
    def test_duplicate_keys_reject_even_if_repinned(self):
        raw=self.raw[:-1]+b',"record_count":2}';self.assertEqual(self.repinned(raw)['decision'],'REJECT')
    def test_duplicate_attempt_reject_even_if_repinned(self):
        body=copy.deepcopy(self.bundle);body['records']=[self.records[0],self.records[0]];self.assertEqual(self.repinned(canonical(body))['decision'],'REJECT')
    def test_nonfinite_and_invalid_utf8_reject(self):
        for raw in (self.raw[:-1]+b',"x":NaN}',b'\xff',b'\xef\xbb\xbf'+self.raw):
            with self.subTest(raw=raw[:8]):self.assertEqual(self.repinned(raw)['decision'],'REJECT')
    def test_deep_nesting_rejects(self):self.assertEqual(self.repinned(b'['*2000+b'0'+b']'*2000)['decision'],'REJECT')
    def test_size_and_input_types_reject(self):
        for raw in (b'',b'x'*(MAX_BYTES+1),'{}',bytearray(b'{}'),None):
            self.assertEqual(review_import(raw,expected_bytes_sha256=self.expected,expected_record_count=2)['decision'],'REJECT')
    def test_boolean_and_numeric_schema_coercion_reject(self):
        for key,value in [('record_count',2.0),('authenticated',0),('may_dispatch',True)]:
            doc=dict(self.bundle,**{key:value});self.assertEqual(self.repinned(canonical(doc))['decision'],'REJECT')
    def test_extra_fields_and_missing_records_reject(self):
        for doc in (dict(self.bundle,credentials='not-exported'),{k:v for k,v in self.bundle.items() if k!='records'}):self.assertEqual(self.repinned(canonical(doc))['decision'],'REJECT')
    def test_expected_count_is_independently_checked(self):self.assertEqual(self.call(count=1)['reason'],'EXPECTED_RECORD_COUNT_MISMATCH')
    def test_internal_export_digest_rejects_even_with_matching_bytes_pin(self):
        doc=dict(self.bundle,export_sha256='f'*64);self.assertEqual(self.repinned(canonical(doc))['decision'],'REJECT')
    def test_record_permission_escalation_rejects_even_if_rehashed(self):
        doc=copy.deepcopy(self.bundle);record=doc['records'][0];record['may_publish']=True;record['record_sha256']=digest({k:v for k,v in record.items() if k!='record_sha256'})
        self.assertEqual(self.repinned(canonical(doc))['decision'],'REJECT')
    def test_input_remains_unchanged(self):
        raw=bytes(self.raw);self.call();self.assertEqual(raw,self.raw)
