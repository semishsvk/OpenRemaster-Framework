"""NW024 synthetic governor policy and state-machine tests."""
import unittest
from governor import Telemetry,Job,Governor
def t(**changes):
 x=dict(cpu_pct=30,gpu_pct=20,ram_pct=40,vram_pct=30,
        cpu_temp_c=60,gpu_temp_c=55,game_detected=False)
 x.update(changes)
 return Telemetry(**x)
def j(i,state="WAITING",heavy=True,checkpointable=True,checkpoint_sha256=None):
 return Job(i,heavy,checkpointable,state,checkpoint_sha256)
class GovernorTests(unittest.TestCase):
 def setUp(self):self.g=Governor()
 def test_normal(self):self.assertEqual(self.g.mode(t())[0],"NORMAL")
 def test_game_light(self):self.assertEqual(self.g.mode(t(game_detected=True))[0],"LIGHT_GAMING")
 def test_auto_default_on(self):self.assertTrue(self.g.auto_game_detection)
 def test_disable_game_auto(self):self.assertEqual(Governor(auto_game_detection=False).mode(t(game_detected=True))[0],"NORMAL")
 def test_manual_disable_not_thermal_bypass(self):self.assertEqual(Governor(auto_game_detection=False).mode(t(cpu_temp_c=91))[0],"EMERGENCY_HOLD")
 def test_cpu_load(self):self.assertEqual(self.g.mode(t(cpu_pct=95))[0],"LIGHT_GAMING")
 def test_gpu_load(self):self.assertEqual(self.g.mode(t(gpu_pct=95))[0],"LIGHT_GAMING")
 def test_ram_load(self):self.assertEqual(self.g.mode(t(ram_pct=89))[0],"LIGHT_GAMING")
 def test_vram_load(self):self.assertEqual(self.g.mode(t(vram_pct=91))[0],"LIGHT_GAMING")
 def test_ram_critical(self):self.assertEqual(self.g.mode(t(ram_pct=96))[0],"EMERGENCY_HOLD")
 def test_vram_critical(self):self.assertEqual(self.g.mode(t(vram_pct=96))[0],"EMERGENCY_HOLD")
 def test_cpu_thermal(self):self.assertEqual(self.g.mode(t(cpu_temp_c=90))[0],"EMERGENCY_HOLD")
 def test_gpu_thermal(self):self.assertEqual(self.g.mode(t(gpu_temp_c=88))[0],"EMERGENCY_HOLD")
 def test_normal_three_heavy_admitted(self):
  r=self.g.plan(t(),[j(str(i)) for i in range(3)])
  self.assertEqual(len(r.admit),3)
 def test_fourth_heavy_blocked(self):
  r=self.g.plan(t(),[j(str(i)) for i in range(4)])
  self.assertEqual(len(r.admit),3)
 def test_running_two_one_admitted(self):
  r=self.g.plan(t(),[j("a","RUNNING"),j("b","RUNNING"),j("c")])
  self.assertEqual(r.admit,("c",))
 def test_running_three_none_admitted(self):
  r=self.g.plan(t(),[j("a","RUNNING"),j("b","RUNNING"),j("c","RUNNING"),j("d")])
  self.assertEqual(r.admit,())
 def test_existing_over_cap_rejected(self):
  with self.assertRaises(ValueError):self.g.plan(t(),[j(str(i),"RUNNING") for i in range(4)])
 def test_light_pauses_checkpointable_heavy(self):
  r=self.g.plan(t(game_detected=True),[j("a","RUNNING")])
  self.assertEqual(r.pause,("a",))
 def test_light_does_not_admit(self):
  self.assertFalse(self.g.plan(t(game_detected=True),[j("a")]).admit)
 def test_emergency_no_admit(self):
  self.assertFalse(self.g.plan(t(cpu_temp_c=92),[j("a")]).admit)
 def test_uncheckpointable_hold_not_force_kill(self):
  r=self.g.plan(t(game_detected=True),[j("a","RUNNING",checkpointable=False)])
  self.assertEqual(r.hold,("a",));self.assertEqual(r.pause,())
 def test_resume_valid_checkpoint(self):
  r=self.g.plan(t(),[j("a","PAUSED",checkpoint_sha256="a"*64)])
  self.assertEqual(r.resume,("a",))
 def test_resume_without_checkpoint_hold(self):
  r=self.g.plan(t(),[j("a","PAUSED")])
  self.assertEqual(r.hold,("a",))
 def test_resume_not_while_gaming(self):
  r=self.g.plan(t(game_detected=True),[j("a","PAUSED",checkpoint_sha256="a"*64)])
  self.assertFalse(r.resume)
 def test_resume_not_while_thermal(self):
  r=self.g.plan(t(cpu_temp_c=95),[j("a","PAUSED",checkpoint_sha256="a"*64)])
  self.assertFalse(r.resume)
 def test_unknown_always_hold(self):
  r=self.g.plan(t(),[j("a","UNKNOWN")])
  self.assertEqual(r.hold,("a",))
 def test_unknown_never_resume(self):
  r=self.g.plan(t(),[j("a","UNKNOWN",checkpoint_sha256="a"*64)])
  self.assertEqual(r.resume,())
 def test_nonheavy_admit_does_not_use_heavy_slot(self):
  r=self.g.plan(t(),[j(str(i),heavy=False) for i in range(6)])
  self.assertEqual(len(r.admit),6)
 def test_heavy_resume_cap(self):
  r=self.g.plan(t(),[j("a","RUNNING"),j("b","RUNNING"),
                      j("c","PAUSED",checkpoint_sha256="a"*64),
                      j("d","PAUSED",checkpoint_sha256="b"*64)])
  self.assertEqual(r.resume,("c",))
 def test_no_real_dispatch(self):
  self.assertFalse(self.g.plan(t(),[j("a")]).may_dispatch)
 def test_no_real_process_mutation(self):
  self.assertFalse(self.g.plan(t(),[j("a")]).real_processes_mutated)
 def test_max_three(self):self.assertEqual(self.g.max_heavy,3)
 def test_max_four_denied(self):
  with self.assertRaises(ValueError):Governor(max_heavy=4)
 def test_bool_max_denied(self):
  with self.assertRaises(ValueError):Governor(max_heavy=True)
 def test_bool_game_setting_denied(self):
  with self.assertRaises(ValueError):Governor(auto_game_detection=1)
 def test_bad_cpu(self):
  with self.assertRaises(ValueError):t(cpu_pct=101)
 def test_nan_cpu(self):
  with self.assertRaises(ValueError):t(cpu_pct=float("nan"))
 def test_bad_temp(self):
  with self.assertRaises(ValueError):t(gpu_temp_c=126)
 def test_bad_game_flag(self):
  with self.assertRaises(ValueError):t(game_detected="yes")
 def test_bad_job_state(self):
  with self.assertRaises(ValueError):j("a","EXECUTING")
 def test_bad_checkpoint_sha(self):
  with self.assertRaises(ValueError):j("a","PAUSED",checkpoint_sha256="fake")
 def test_duplicate_job_id(self):
  with self.assertRaises(ValueError):self.g.plan(t(),[j("a"),j("a")])
 def test_empty_plan(self):self.assertFalse(self.g.plan(t(),[]).admit)
 def test_finished_not_resumed(self):
  r=self.g.plan(t(),[j("a","FINISHED",checkpoint_sha256="a"*64)])
  self.assertEqual((r.admit,r.resume), ((),()))
 def test_game_reason(self):
  self.assertIn("AUTO_GAME_DETECTED",self.g.plan(t(game_detected=True),[]).reason_codes)
 def test_thermal_reason(self):
  self.assertIn("THERMAL_LIMIT",self.g.plan(t(cpu_temp_c=100),[]).reason_codes)
if __name__=="__main__":unittest.main()
