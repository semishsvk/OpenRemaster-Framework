import unittest,tempfile,json
from pathlib import Path
from dynamic_scheduler_core_v1 import Task,Worker
from dynamic_scheduler_durable_v1 import run_synthetic,verify_synthetic
def task(p,i):return Task(p,p+str(i),10-i,("cpu",),True,True,True,True,True,True)
W=[Worker("w"+str(i),("cpu",),True,True) for i in range(3)]
class DurableTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/"run"
 def tearDown(self):self.tmp.cleanup()
 def make(self):
  tasks=[task(p,i) for i,p in enumerate(("A","B","C","D","E"))]
  return run_synthetic(self.root,tasks,W,{t.task_id:"PASS" for t in tasks},"r1")
 def test_sealed_chain(self):
  r=self.make();self.assertEqual(r["events"],5);self.assertTrue(verify_synthetic(self.root))
 def test_no_overwrite(self):
  self.make()
  with self.assertRaises(FileExistsError):self.make()
 def test_tamper_event(self):
  self.make();p=self.root/"event-000000.json";d=json.loads(p.read_text());d["event"]["result"]="FAIL";p.write_text(json.dumps(d))
  self.assertFalse(verify_synthetic(self.root))
 def test_tamper_input(self):
  self.make();p=self.root/"inputs.json";d=json.loads(p.read_text());d["run_id"]="altered";p.write_text(json.dumps(d))
  self.assertFalse(verify_synthetic(self.root))
 def test_zero_work(self):
  r=run_synthetic(self.root,[],W,{},"empty")
  self.assertEqual(r["events"],0);self.assertTrue(verify_synthetic(self.root))
 def test_no_native(self):
  self.assertFalse(self.make()["native_execution"])
if __name__=="__main__":unittest.main(verbosity=2)
