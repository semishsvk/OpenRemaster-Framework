import copy,hashlib,unittest
from admission_boundary_base import canonical
from resource_observation import review_resource_observation
import test_work_identity as fixture

class ResourceObservationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.WorkIdentityTests(methodName='test_all_bindings_preserved_but_no_resource_authority');self.f.setUp()
        self.inputs=dict(envelope=self.f.envelope,request=self.f.request,grant=self.f.grant,poa_request=self.f.poa_request,job_bytes=self.f.job)
        digest=hashlib.sha256(canonical(self.f.call())).hexdigest()
        self.expected=dict(authority_id='synthetic-resource',source_id='synthetic-telemetry',policy_version='synthetic-policy',owner_fence=7,resource_fence=3,last_sequence=10,max_age_seconds=10,work_identity_sha256=digest)
        self.obs=dict(schema='OpenRemaster.ResourceObservation.v1',authority_id='synthetic-resource',source_id='synthetic-telemetry',policy_version='synthetic-policy',project_id='SYNTHETIC',operation_id=self.f.binding['operation_id'],owner_fence=7,resource_fence=3,work_identity_sha256=digest,sequence=11,observed_at=self.f.now-1,valid_until=self.f.now+5,telemetry=dict(cpu_pct=10,gpu_pct=10,ram_pct=10,vram_pct=10,cpu_temp_c=50,gpu_temp_c=50,game_detected=False),jobs=[self.job('synthetic-job')])
    def job(self,name,**kw):return dict(dict(job_id=name,heavy=True,checkpointable=True,state='WAITING',checkpoint_sha256=None),**kw)
    def call(self,**kw):
        args=dict(expected_identity=self.f.expected,expected_resource=self.expected,owner_keys={'owner-fixture':self.f.owner},envelope_keys={'ed-fixture':self.f.public},now=self.f.now);args.update(kw)
        return review_resource_observation(self.inputs,self.obs,**args)
    def test_normal_proposal_still_has_no_authority_or_consumption(self):
        r=self.call();self.assertTrue(r['resource_checks_satisfied']);self.assertEqual(r['reason'],'RESOURCE_AUTHORITY_UNAVAILABLE')
        for key in ('resource_authority_verified','independent_authority_verified','observation_consumed','nonce_reserved','dispatch_authorized','may_dispatch','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_go'):self.assertIs(r[key],False)
        self.assertFalse(r['proposal']['may_dispatch']);self.assertEqual(r['proposal']['max_heavy'],3)
    def test_missing_resource_context_holds(self):self.assertEqual(self.call(expected_resource=None)['reason'],'RESOURCE_CONTEXT_REQUIRED')
    def test_stale_and_invalid_intervals_hold(self):
        for start,end in [(self.f.now-20,self.f.now-10),(self.f.now-1,self.f.now),(self.f.now-1,self.f.now+20),(self.f.now,self.f.now)]:
            self.obs.update(observed_at=start,valid_until=end);self.assertEqual(self.call()['reason'],'OBSERVATION_STALE_OR_INVALID_INTERVAL')
    def test_future_observation_rejected(self):
        self.obs.update(observed_at=self.f.now+1,valid_until=self.f.now+2);self.assertEqual(self.call()['reason'],'OBSERVATION_FROM_FUTURE')
    def test_every_observation_binding_mismatch_rejected(self):
        for key,value in [('authority_id','foreign'),('source_id','foreign'),('policy_version','other'),('owner_fence',8),('resource_fence',4),('work_identity_sha256','0'*64),('project_id','FOREIGN'),('operation_id','e'*32)]:
            obs=copy.deepcopy(self.obs);obs[key]=value
            r=review_resource_observation(self.inputs,obs,expected_identity=self.f.expected,expected_resource=self.expected,owner_keys={'owner-fixture':self.f.owner},envelope_keys={'ed-fixture':self.f.public},now=self.f.now)
            self.assertEqual(r['decision'],'REJECT',key)
    def test_resource_context_cannot_rebind_work_identity(self):
        for key,value in [('work_identity_sha256','0'*64),('resource_fence',4),('owner_fence',8),('policy_version','other')]:
            expected=dict(self.expected,**{key:value});self.assertEqual(self.call(expected_resource=expected)['decision'],'REJECT',key)
    def test_reused_or_lower_sequence_rejected_against_highwater(self):
        for sequence in (1,10):self.obs['sequence']=sequence;self.assertEqual(self.call()['reason'],'OBSERVATION_SEQUENCE_REPLAY_OR_STALE')
        self.obs['sequence']=11;self.expected['last_sequence']=11;self.assertEqual(self.call()['reason'],'OBSERVATION_SEQUENCE_REPLAY_OR_STALE')
    def test_repeated_calls_never_consume_or_authorize(self):
        a=self.call();b=self.call();self.assertEqual(a,b);self.assertFalse(b['observation_consumed']);self.assertEqual(b['decision'],'HOLD')
    def test_game_light_blocks_admission(self):
        self.obs['telemetry']['game_detected']=True;self.assertEqual(self.call()['reason'],'GOVERNOR_LIGHT_GAMING')
    def test_resource_load_uses_existing_governor(self):
        self.obs['telemetry']['cpu_pct']=95;self.assertEqual(self.call()['reason'],'GOVERNOR_LIGHT_GAMING')
    def test_thermal_and_memory_emergency_hold(self):
        for field,value in [('cpu_temp_c',95),('gpu_temp_c',90),('ram_pct',97),('vram_pct',97)]:
            old=copy.deepcopy(self.obs['telemetry']);self.obs['telemetry'][field]=value
            self.assertEqual(self.call()['reason'],'GOVERNOR_EMERGENCY_HOLD');self.obs['telemetry']=old
    def test_unknown_execution_blocks_even_with_capacity(self):
        self.obs['jobs'].append(self.job('unknown',state='UNKNOWN'));self.assertEqual(self.call()['reason'],'UNKNOWN_EXECUTION_NO_RETRY')
    def test_fourth_heavy_job_not_admitted(self):
        self.obs['jobs']=[self.job(str(i),state='RUNNING') for i in range(3)]+[self.job('synthetic-job')]
        self.assertEqual(self.call()['reason'],'CAPACITY_OR_GOVERNOR_HOLD')
    def test_existing_over_capacity_rejected(self):
        self.obs['jobs']=[self.job(str(i),state='RUNNING') for i in range(4)]+[self.job('synthetic-job')]
        self.assertEqual(self.call()['decision'],'REJECT')
    def test_target_identity_and_heavy_flag_are_bound(self):
        for rows in ([],[self.job('foreign')],[self.job('synthetic-job',heavy=False)]):
            self.obs['jobs']=rows;self.assertEqual(self.call()['reason'],'TARGET_JOB_BINDING_MISMATCH')
    def test_duplicate_jobs_rejected(self):
        self.obs['jobs']*=2;self.assertEqual(self.call()['decision'],'REJECT')
    def test_invalid_telemetry_and_schema_rejected(self):
        self.obs['telemetry']['game_detected']='false';self.assertEqual(self.call()['decision'],'REJECT')
        self.obs['telemetry']['game_detected']=False;self.obs['telemetry']['cpu_pct']=float('nan');self.assertEqual(self.call()['decision'],'REJECT')
    def test_boolean_time_sequence_and_fence_rejected(self):
        for key in ('observed_at','valid_until','sequence','owner_fence','resource_fence'):
            old=self.obs[key];self.obs[key]=True;self.assertEqual(self.call()['decision'],'REJECT',key);self.obs[key]=old
    def test_precomputed_identity_report_is_not_accepted(self):
        self.inputs=self.f.call();self.assertEqual(self.call()['reason'],'IDENTITY_INPUT_SCHEMA')
    def test_forged_signed_work_rejected_before_governor(self):
        self.f.grant['signature']='0'*64;self.assertEqual(self.call()['decision'],'REJECT')
    def test_extra_claims_and_oversized_jobs_rejected(self):
        self.obs['verified']=True;self.assertEqual(self.call()['reason'],'OBSERVATION_SCHEMA');del self.obs['verified']
        self.obs['jobs']=[self.job(str(i)) for i in range(1025)];self.assertEqual(self.call()['reason'],'JOB_BOUND')
    def test_input_and_returned_evidence_detached(self):
        before=copy.deepcopy((self.obs,self.expected));r=self.call();r['proposal']['admit']=('mutated',)
        self.assertEqual(before,(self.obs,self.expected))
    def test_paused_or_running_target_not_new_admission(self):
        for state in ('RUNNING','PAUSED','FINISHED'):
            self.obs['jobs'][0]['state']=state;self.assertEqual(self.call()['reason'],'TARGET_NOT_WAITING')
    def test_invalid_external_resource_context_fails_closed(self):
        for key,value in [('max_age_seconds',31),('max_age_seconds',0),('last_sequence',True),('work_identity_sha256',float('nan')),('work_identity_sha256',{}),('resource_fence',True)]:
            expected=dict(self.expected,**{key:value});self.assertEqual(self.call(expected_resource=expected)['reason'],'RESOURCE_CONTEXT_INVALID')
