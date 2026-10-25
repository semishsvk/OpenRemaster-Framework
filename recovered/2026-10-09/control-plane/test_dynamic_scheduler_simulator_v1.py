import unittest
from dynamic_scheduler_core_v1 import Task,Worker
from dynamic_scheduler_simulator_v1 import simulate
def t(name,priority):
 return Task(name,name+"-job",priority,("cpu",),True,True,True,True,True,True,True)
W=[Worker("w"+str(i),("cpu",),True,True) for i in range(3)]
class Tests(unittest.TestCase):
 def test_dynamic_rotation(self):
  tasks=[t(x,10-i) for i,x in enumerate(("A","B","C","D","E","F","G"))]
  r=simulate(tasks,W,{x.task_id:"PASS" for x in tasks})
  self.assertEqual(r["status"],"SIMULATION_COMPLETE")
  self.assertEqual([e["tick"] for e in r["events"]],[0,0,0,1,1,1,2])
 def test_blocker_does_not_block_others(self):
  tasks=[t(x,10-i) for i,x in enumerate(("A","B","C","D"))]
  r=simulate(tasks,W,{x.task_id:("BLOCKED" if x.project=="A" else "PASS") for x in tasks})
  self.assertEqual(r["status"],"SIMULATION_COMPLETE")
  self.assertEqual(r["events"][-1]["project"],"D")
 def test_no_workers(self):
  r=simulate([t("A",1)],[],{"A-job":"PASS"})
  self.assertEqual(r["status"],"BLOCKED")
 def test_missing_outcome_fails_closed(self):
  with self.assertRaises(ValueError):simulate([t("A",1)],W,{})
 def test_no_native_execution(self):
  r=simulate([t("A",1)],W,{"A-job":"PASS"})
  self.assertFalse(r["native_execution"]);self.assertFalse(r["leases_modified"])
 def test_no_duplicate(self):
  with self.assertRaises(ValueError):simulate([t("A",2),t("A",1)],W,{"A-job":"PASS"})
if __name__=="__main__":unittest.main(verbosity=2)
