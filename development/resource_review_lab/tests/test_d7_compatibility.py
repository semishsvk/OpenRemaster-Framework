import copy,hashlib,json,unittest
from admission_boundary_base import canonical
from d7_compatibility import review_d7_compatibility
import test_resource_observation as fixture

class D7CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.r=fixture.ResourceObservationTests(methodName='test_normal_proposal_still_has_no_authority_or_consumption');self.r.setUp();self.f=self.r.f
    def call(self,request=None,**kw):return review_d7_compatibility(self.f.request if request is None else request,self.r.inputs,self.r.obs,expected_identity=self.f.expected,expected_resource=self.r.expected,owner_keys={'owner-fixture':self.f.owner},envelope_keys={'ed-fixture':self.f.public},now=self.f.now,**kw)
    def job(self,kind='executable_runtime'):
        return dict(schema='ORCH-K003.Job.v1',job_id=self.f.binding['job_id'],project='SYNTHETIC',task='synthetic-dev-build',inputs=[],required_capabilities=['build_studio_dev'],execution=dict(kind=kind,executable='synthetic-tool-only'),validation=dict(expected_exit_code=0))
    def rebind(self,job):
        self.f.job=canonical(job);self.f.binding['job_sha256']=hashlib.sha256(self.f.job).hexdigest();self.f.resign()
        self.f.expected=dict(binding=copy.deepcopy(self.f.binding),shadow_context=copy.deepcopy(self.f.context))
        digest=hashlib.sha256(canonical(self.f.call())).hexdigest()
        self.r.inputs=dict(envelope=self.f.envelope,request=self.f.request,grant=self.f.grant,poa_request=self.f.poa_request,job_bytes=self.f.job)
        self.r.expected['work_identity_sha256']=digest;self.r.obs['work_identity_sha256']=digest
    def test_minimal_synthetic_poa_job_is_not_a_full_k003_job(self):
        r=self.call();self.assertTrue(r['checks']['identity_resource_contract_matches']);self.assertFalse(r['checks']['k003_shape_matches']);self.assertEqual(r['reason'],'K003_JOB_DOES_NOT_MATCH_EXISTING_SCHEMA')
    def test_runtime_shape_is_not_implicit_dev_build_execution(self):
        self.rebind(self.job());r=self.call();self.assertTrue(r['checks']['k003_shape_matches']);self.assertFalse(r['checks']['d7_build_kind_supported'])
        self.assertEqual(r['reason'],'D7_BUILD_KIND_NOT_SUPPORTED_BY_PINNED_K003_NO_EXECUTABLE_FALLBACK')
        for key in ('worker_called','k003_invoked','query_performed','receipt_created','independent_admission_verified','production_signature_required_for_development','dispatch_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[key],False)
    def test_named_dev_kind_not_added_to_schema(self):
        self.rebind(self.job('build_studio_dev'));self.assertEqual(self.call()['reason'],'K003_JOB_DOES_NOT_MATCH_EXISTING_SCHEMA')
    def test_status_remains_query_only_and_does_not_query_worker(self):
        r=self.call(dict(self.f.request,action='status'));self.assertEqual(r['reason'],'D7_STATUS_QUERY_ONLY_NO_EXECUTION_OR_QUERY_PERFORMED');self.assertFalse(r['query_performed']);self.assertFalse(r['worker_called'])
    def test_status_cannot_cross_operation(self):
        self.assertEqual(self.call(dict(self.f.request,action='status',operation_id='e'*32))['reason'],'D7_REQUEST_IDENTITY_MISMATCH')
    def test_unknown_extra_fields_reject_implicit_admission_upgrade(self):
        self.assertEqual(self.call(dict(self.f.request,admission_envelope={}))['reason'],'D7_REQUEST_SCHEMA')
    def test_invalid_action_capability_or_operation_holds(self):
        for key,value in [('action','release'),('scenario','publish.production'),('operation_id',True),('operation_id','x'*32)]:self.assertEqual(self.call(dict(self.f.request,**{key:value}))['reason'],'D7_REQUEST_SCOPE')
    def test_unsigned_dev_label_not_a_reason_to_require_production_key(self):
        r=self.call();self.assertFalse(r['production_signature_required_for_development']);self.assertEqual(r['decision'],'HOLD')
    def test_missing_independent_context_never_falls_back(self):
        self.f.expected=None;self.assertEqual(self.call()['reason'],'EXPECTED_IDENTITY_REQUIRED')
    def test_resource_unknown_prevents_compatibility_claim(self):
        self.r.obs['jobs'].append(self.r.job('unknown',state='UNKNOWN'));r=self.call();self.assertFalse(r['checks']['identity_resource_contract_matches']);self.assertIn('UNKNOWN_EXECUTION',r['reason'])
    def test_mismatched_signed_request_holds(self):
        self.r.inputs['request']=dict(self.f.request,action='status');self.assertEqual(self.call()['reason'],'D7_SIGNED_REQUEST_MISMATCH')
    def test_changed_job_bytes_cannot_reuse_prior_proof(self):
        self.r.inputs['job_bytes']+=b' ';self.assertFalse(self.call()['checks']['identity_resource_contract_matches'])
    def test_k003_missing_required_validation_not_accepted(self):
        job=self.job();del job['validation'];self.rebind(job);self.assertEqual(self.call()['reason'],'K003_JOB_DOES_NOT_MATCH_EXISTING_SCHEMA')
    def test_input_is_not_mutated(self):
        before=copy.deepcopy((self.f.request,self.f.expected,self.r.obs));self.call();self.assertEqual(before,(self.f.request,self.f.expected,self.r.obs))
    def receipt(self):return dict(schema='OpenRemaster.DevWorkflowResult.v1',operation_id=self.f.request['operation_id'],state='COMMITTED',production_go=False,worker=dict(success=True,build_plan_sha256='a'*64,source_manifest_sha256='b'*64,artifacts=dict(profile='DEV_UNSIGNED',signature_status='NotSigned')))
    def test_existing_unsigned_result_observer_reused_without_release(self):
        r=self.call(dev_result=self.receipt());self.assertTrue(r['checks']['dev_result_observed']);self.assertFalse(r['dev_receipt_observation']['release_eligible']);self.assertFalse(r['dispatch_authorized']);self.assertFalse(r['production_signature_required_for_development'])
    def test_result_operation_cannot_cross_request(self):
        receipt=self.receipt();receipt['operation_id']='e'*32;self.assertEqual(self.call(dev_result=receipt)['reason'],'DEV_RESULT_OPERATION_MISMATCH')
    def test_result_production_claim_holds(self):
        receipt=self.receipt();receipt['production_go']=True;self.assertEqual(self.call(dev_result=receipt)['reason'],'DEV_RESULT_PRODUCTION_OVERCLAIM')
    def test_unknown_result_schema_holds(self):
        receipt=self.receipt();receipt['schema']='UNKNOWN';self.assertEqual(self.call(dev_result=receipt)['reason'],'DEV_RESULT_SCHEMA')
    def test_no_result_required_for_prebuild_contract_review(self):
        self.assertIsNone(self.call()['dev_receipt_observation'])
