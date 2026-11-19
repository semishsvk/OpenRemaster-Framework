import unittest,tempfile,json
from pathlib import Path
from dynamic_scheduler_queue_v1 import proposal
from dynamic_scheduler_dispatch_guard_v1 import validate_dispatch
class GuardTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
  self.pool=p/"pool.json";self.cap=p/"capacity.json";self.out=p/"proposal.json";self.job=p/"job.json"
  self.pool.write_text(json.dumps({"schema":"OpenRemaster.TaskPool.v1","tasks":[dict(project="OpenMDK1",task_id="mdk-probe",priority=10,capabilities=["cpu"],scope_approved=True,hashes_verified=True,dependencies_ready=True,admission_valid=True,lease_valid=True,writer_available=True,heavy=True)]}))
  self.cap.write_text(json.dumps({"schema":"OpenRemaster.CapacitySnapshot.v1","complete":True,"fresh":True,"source_authorized":True,"running":[],"workers":[dict(worker_id="worker1",capabilities=["cpu"],commissioned=True,available=True)]}))
  self.job.write_text(json.dumps({"schema":"ORCH-K003.Job.v1","job_id":"synthetic1","project":"OpenMDK1","task":"mdk-probe","required_capabilities":["cpu"],"execution":{"kind":"executable_runtime"}}))
  proposal(self.pool,self.cap,self.out)
 def tearDown(self):self.tmp.cleanup()
 def check(self):return validate_dispatch(self.out,self.pool,self.cap,self.job,"worker1")
 def test_valid_is_not_execution_authority(self):
  self.assertEqual(self.check()["status"],"READY_FOR_SEPARATE_ADMISSION")
 def test_stale_snapshot(self):
  d=json.loads(self.cap.read_text());d["running"].append(dict(project="B",worker_id="w2",heavy=True));self.cap.write_text(json.dumps(d))
  self.assertEqual(self.check()["reason"],"STALE_INPUT")
 def test_unassigned_task(self):
  d=json.loads(self.job.read_text());d["task"]="different";self.job.write_text(json.dumps(d))
  self.assertEqual(self.check()["reason"],"UNASSIGNED_JOB")
 def test_worker_mismatch(self):
  self.assertEqual(validate_dispatch(self.out,self.pool,self.cap,self.job,"unknown")["reason"],"UNASSIGNED_JOB")
 def test_capability_mismatch(self):
  d=json.loads(self.job.read_text());d["required_capabilities"]=["gpu"];self.job.write_text(json.dumps(d))
  self.assertEqual(self.check()["reason"],"CAPABILITY_MISMATCH")
 def test_unsupported_execution(self):
  d=json.loads(self.job.read_text());d["execution"]={"kind":"shell"};self.job.write_text(json.dumps(d))
  self.assertEqual(self.check()["reason"],"UNSUPPORTED_EXECUTION")
if __name__=="__main__":unittest.main(verbosity=2)
