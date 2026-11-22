import unittest
from dynamic_scheduler_core_v1 import Task,Worker,plan
def task(p,**kwargs):
 d=dict(project=p,task_id=p+"-001",priority=10,capabilities=("cpu",),scope_approved=True,
 hashes_verified=True,dependencies_ready=True,admission_valid=True,lease_valid=True,
 writer_available=True,heavy=True)
 d.update(kwargs);return Task(**d)
W=[Worker(f"w{i}",("cpu",),True,True) for i in range(4)]
class SchedulerTests(unittest.TestCase):
 def test_three_slots(self):
  r=plan([task(str(i)) for i in range(5)],W)
  self.assertEqual(len(r["assignments"]),3)
 def test_no_fourth_heavy(self):
  r=plan([task("next")],W,[dict(project=str(i),worker_id=f"w{i}",heavy=True) for i in range(3)])
  self.assertEqual(len(r["assignments"]),0)
 def test_wip(self):
  r=plan([task("A"),task("A",task_id="A-002")],W)
  self.assertEqual(len(r["assignments"]),1)
 def test_azrael_excluded(self):
  self.assertEqual(plan([task("OpenAzrael-Retail"),task("OpenAzrael-Demo")],W)["assignments"],[])
 def test_fail_closed(self):
  for field in ("scope_approved","hashes_verified","dependencies_ready","admission_valid","lease_valid","writer_available"):
   self.assertEqual(plan([task("A",**{field:False})],W)["assignments"],[],field)
 def test_missing_running_accounting(self):
  self.assertEqual(plan([task("A")],W,[{"project":"other"}])["status"],"BLOCKED")
 def test_blocked_project_rebalances(self):
  r=plan([task("A",lease_valid=False,priority=100),task("B")],W)
  self.assertEqual(r["assignments"][0]["project"],"B")
 def test_capabilities(self):
  self.assertEqual(plan([task("A",capabilities=("gpu",))],W)["assignments"],[])
 def test_running_project_excluded(self):
  r=plan([task("A"),task("B")],W,[dict(project="A",worker_id="w0",heavy=True)])
  self.assertEqual([x["project"] for x in r["assignments"]],["B"])
 def test_nonpreemptive(self):
  r=plan([task("A",priority=100)],W,[dict(project="B",worker_id="w0",heavy=True)])
  self.assertEqual(r["assignments"][0]["worker_id"],"w1")
if __name__=="__main__":unittest.main(verbosity=2)
