import hashlib,tempfile,unittest
from pathlib import Path
from dynamic_scheduler_supervisor_probe_v1 import execute_fixture,sha
class SupervisorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name);self.script=self.p/"fixture.py"
 def tearDown(self):self.tmp.cleanup()
 def write(self,s):self.script.write_text(s);return sha(self.script)
 def test_success(self):
  h=self.write("print('ok')");r=execute_fixture(self.script,h,self.p)
  self.assertEqual(r["status"],"PASS");self.assertTrue(r["process_stopped_verified"])
 def test_nonzero_exit(self):
  h=self.write("raise SystemExit(3)");r=execute_fixture(self.script,h,self.p)
  self.assertEqual(r["status"],"FAIL");self.assertEqual(r["exit_code"],3)
 def test_timeout(self):
  h=self.write("import time;time.sleep(3)");r=execute_fixture(self.script,h,self.p,0.2)
  self.assertEqual(r["status"],"BLOCKED");self.assertTrue(r["timed_out"]);self.assertTrue(r["process_stopped_verified"])
 def test_hash_drift(self):
  h=self.write("print(1)");self.script.write_text("print(2)")
  self.assertEqual(execute_fixture(self.script,h,self.p)["reason"],"SOURCE_HASH_MISMATCH")
 def test_path_escape(self):
  other=self.p/"child";other.mkdir();s=other/"fixture.py";s.write_text("print(1)")
  self.assertEqual(execute_fixture(s,sha(s),self.p)["reason"],"OUTSIDE_ISOLATED_WORKDIR")
 def test_invalid_timeout(self):
  h=self.write("print(1)")
  self.assertEqual(execute_fixture(self.script,h,self.p,60)["reason"],"TIMEOUT_BUDGET")
if __name__=="__main__":unittest.main(verbosity=2)
