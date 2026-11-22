"""Independent positive/negative DOSBox-X integration mouse result.
Reads ten bytes written by each genuine 16-bit DOS COM to private overlay.
Does NOT infer an original Zork game menu selection from this test.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,struct,hashlib
R=Path(__file__).resolve().parents[2]
runs=R/"runtime-test"/"results"
directory=R/"work"/"OpenZork"/"staging"/"dosboxx-integration-mouse-20261009-v8-r2"
fixture=directory/"guest"/"IGPROBE.COM"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
cases=[]
for mode in ("enabled","disabled"):
 rid="openzork-dosboxx-igmouse-canary-20261009-"+mode
 run=runs/rid
 result=json.loads((run/"result.json").read_text(encoding="utf-8-sig"))
 capture=result.get("capture_evidence") or {}
 produced=run/"fidelity-isolated"/"overlay"/"IGMOUSE.BIN"
 case={"mode":mode,
       "guest_program_executed":produced.is_file(),
       "supervisor_diagnostic_status":result.get("diagnostic_capture_status"),
       "process_exit":result.get("exit_code"),
       "registered_executable_hash":(result.get("registered_target") or {}).get("executable_sha256"),
       "game_root_binding":(result.get("game_source_binding") or {}).get("config_game_root"),
       "original_data_source_modified":False}
 if produced.is_file():
  b=produced.read_bytes()
  case["file_size"]=len(b)
  case["file_sha256"]=sha(produced)
  case["hex"]=b.hex()
  if len(b)==10:
   magic,reset,press,release=struct.unpack("<IHHH",b)
   case.update({"integration_identification":hex(magic),
         "integration_magic_match":magic==0xd05b0740,
         "int33_mouse_reset_AX":hex(reset),
         "mouse_pressed_BX":press,
         "mouse_released_BX":release,
         "emulated_mouse_button_state_changed":press==1 and release==0})
 cases.append(case)
good=len(cases)==2 and all(c["guest_program_executed"]
                 and c["process_exit"]==0 and c["supervisor_diagnostic_status"]=="PASS"
                 and c.get("file_size")==10 for c in cases)
pos,neg=cases
expected=(good and pos.get("integration_magic_match") is True
          and pos.get("emulated_mouse_button_state_changed") is True
          and neg.get("integration_magic_match") is False
          and neg.get("emulated_mouse_button_state_changed") is False)
status="DOSBOX_X_INTERNAL_GUEST_MOUSE_DEVICE_POSITIVE_NEGATIVE_PASS" if expected else "INTEGRATION_DEVICE_OR_MOUSE_PROOF_HOLD"
report={
 "schema":"OpenZork.DOSBoxXNativeIntegrationMouseCANARY.v1",
 "date_utc":datetime.now(timezone.utc).isoformat(),
 "status":status,
 "binary_fixture":str(fixture),
 "binary_fixture_sha256":sha(fixture),
 "positive_vs_negative":cases,
 "scope":"REGISTERED_ORIGINAL_ZORK_DOSBOX_X_EMULATOR_WITH_PRIVATE_READ_ONLY_GUEST_UTILITY",
 "game_ZORKDOS_executable_was_run":False,
 "global_Windows_mouse_or_keyboard_modified":False,
 "source_game_corpus_was_modified":False,
 "canary_original_game_menu_selection":"NOT_TESTED",
 "fidelity_promoted":False}
out=runs/"dosboxx-integration-guest-mouse-positive-negative-v8.json"
if out.exists():raise RuntimeError("RECEIPT_EXISTS_NO_OVERWRITE")
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":status,"cases":cases,"evidence":str(out)},ensure_ascii=False))
raise SystemExit(0 if expected else 1)
