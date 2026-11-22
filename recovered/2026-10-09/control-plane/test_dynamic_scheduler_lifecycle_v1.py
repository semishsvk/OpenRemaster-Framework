import unittest
from dynamic_scheduler_lifecycle_v1 import transition,recovery_action
class LifecycleTests(unittest.TestCase):
 def test_happy_path(self):
  seq=[("PROPOSED","ADMISSION_PENDING",{}),("ADMISSION_PENDING","ADMITTED",dict(admission_id="a",worker_id="w")),
   ("ADMITTED","LEASED",dict(lease_id="l",fencing_epoch=1)),
   ("LEASED","RUNNING",dict(pid=123,start_utc="t")),
   ("RUNNING","VALIDATING",dict(exit_code=0,result_sha256="abc")),
   ("VALIDATING","PASS",dict(validation_sha256="v",checkpoint_sha256="c",process_tree_stopped=True))]
  for a,b,ev in seq:self.assertEqual(transition(a,b,dict(ev,verified=True))["status"],"ACCEPTED")
 def test_no_unverified_promotion(self):
  self.assertEqual(transition("VALIDATING","PASS",{"verified":False})["reason"],"MISSING_VERIFIED_EVIDENCE")
 def test_no_missing_checkpoint(self):
  self.assertEqual(transition("VALIDATING","PASS",dict(verified=True,validation_sha256="v",process_tree_stopped=True))["reason"],"INCOMPLETE_TRANSITION_EVIDENCE")
 def test_no_running_without_lease(self):
  self.assertEqual(transition("ADMITTED","RUNNING",{"verified":True})["reason"],"ILLEGAL_TRANSITION")
 def test_terminal_immutable(self):
  self.assertEqual(transition("PASS","RUNNING",{"verified":True})["reason"],"ILLEGAL_TRANSITION")
 def test_no_stop_no_release(self):
  self.assertNotEqual(transition("VALIDATING","PASS",dict(verified=True,validation_sha256="v",checkpoint_sha256="c",process_tree_stopped=False))["status"],"ACCEPTED")
 def test_recovery_unknown_process(self):
  self.assertEqual(recovery_action(dict(source_hash_verified=True,state="RUNNING",process_tree_status="UNKNOWN")),"BLOCKED_RECONCILE_PROCESS_TREE")
 def test_recovery_stale_lease(self):
  self.assertEqual(recovery_action(dict(source_hash_verified=True,state="RUNNING",process_tree_status="STOPPED_VERIFIED",lease_status="ACTIVE")),"BLOCKED_RECONCILE_LEASE")
 def test_recovery_good(self):
  self.assertEqual(recovery_action(dict(source_hash_verified=True,state="RUNNING",process_tree_status="STOPPED_VERIFIED",lease_status="RELEASED_VERIFIED",checkpoint_verified=True)),"ELIGIBLE_FOR_NEW_ADMISSION")
 def test_recovery_bad_hash(self):
  self.assertEqual(recovery_action(dict(source_hash_verified=False,state="RUNNING")),"QUARANTINE")
if __name__=="__main__":unittest.main(verbosity=2)
