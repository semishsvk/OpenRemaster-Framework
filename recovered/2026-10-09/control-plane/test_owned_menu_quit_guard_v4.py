"""Negative policy: menu quit can only operate on DOSBox-X owned window.
Also verify the already recorded real owned-menu receipt and clean process exit.
"""
import json,os
from pathlib import Path
from fidelity_runtime_isolation_v1 import IsolationError
from fidelity_owned_window_menu_v1 import post_bound_dosboxx_quit
def expect(reason,fn):
 try:fn()
 except IsolationError as e:
  assert e.reason==reason,(e.reason,reason);return
 raise AssertionError("Expected safe rejection: "+reason)
expect("OWNED_MENU_QUIT_REQUIRES_DOSBOX_X",
       lambda:post_bound_dosboxx_quit(1,os.getpid(),1,"not-dosbox-x.exe"))
root=Path(__file__).resolve().parents[2]
rid="openzork-dosboxx-late-autotype-e5946df0ec"
out=root/"runtime-test"/"results"/rid
r=json.loads((out/"result.json").read_text(encoding="utf-8"))
receipt=r.get("owned_dosboxx_menu_quit") or {}
assert r["diagnostic_capture_status"]=="PASS" and r.get("exit_code")==0
assert receipt.get("menu_label")=="Quit from DOSBox-X"
assert receipt.get("menu_id")==4100 and receipt.get("global_input_used") is False
assert r.get("fidelity_verified") is not True
print(json.dumps({"schema":"OpenRemaster.OwnedDOSBoxXMenuQuitCanary.v1",
"status":"PASS","unrelated_executable_rejected":True,
"observed_real_menu_label":receipt["menu_label"],
"observed_actual_clean_exit":0,
"no_global_input":True,"original_fidelity_not_attested":True}))
