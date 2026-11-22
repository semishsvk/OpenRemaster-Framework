import tempfile,json,unittest
from pathlib import Path
from dynamic_scheduler_queue_v1 import proposal
def task(p,priority=10):
 return dict(project=p,task_id=p+"-1",priority=priority,capabilities=["cpu"],scope_approved=True,hashes_verified=True,dependencies_ready=True,admission_valid=True,lease_valid=True,writer_available=True,heavy=True)
class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.pool=self.root/"pool.json";self.cap=self.root/"cap.json";self.out=self.root/"receipt.json"
  self.pool.write_text(json.dumps({"schema":"OpenRemaster.TaskPool.v1","tasks":[task("A",20),task("B",10),task("C",5),task("D",1)]}))
  self.cap.write_text(json.dumps({"schema":"OpenRemaster.CapacitySnapshot.v1","complete":True,"fresh":True,"source_authorized":True,"running":[],"workers":[dict(worker_id="w"+str(i),capabilities=["cpu"],commissioned=True,available=True) for i in range(3)]}))
 def tearDown(self):self.tmp.cleanup()
 def test_three_assignments_and_immutable(self):
  r=proposal(self.pool,self.cap,self.out);self.assertEqual(len(r["result"]["assignments"]),3)
  with self.assertRaises(FileExistsError):proposal(self.pool,self.cap,self.out)
 def test_capacity_fail_closed(self):
  d=json.loads(self.cap.read_text());d["fresh"]=False;self.cap.write_text(json.dumps(d))
  with self.assertRaises(ValueError):proposal(self.pool,self.cap,self.out)
  self.assertFalse(self.out.exists())
 def test_rebalance_after_completion(self):
  first=proposal(self.pool,self.cap,self.out)
  self.assertEqual([x["project"] for x in first["result"]["assignments"]],["A","B","C"])
  d=json.loads(self.cap.read_text());d["running"]=[dict(project="B",worker_id="w1",heavy=True)];self.cap.write_text(json.dumps(d))
  second=proposal(self.pool,self.cap,self.root/"next.json")
  self.assertEqual([x["project"] for x in second["result"]["assignments"]],["A","C"])
 def test_no_capacity(self):
  d=json.loads(self.cap.read_text());d["running"]=[dict(project=p,worker_id="w"+str(i),heavy=True) for i,p in enumerate(("A","B","C"))];self.cap.write_text(json.dumps(d))
  self.assertEqual(proposal(self.pool,self.cap,self.out)["result"]["assignments"],[])
 def test_no_dispatch(self):
  r=proposal(self.pool,self.cap,self.out)
  self.assertFalse(r["dispatch_executed"]);self.assertFalse(r["lease_modified"])
if __name__=="__main__":unittest.main(verbosity=2)
