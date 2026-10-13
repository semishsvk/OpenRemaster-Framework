"""False positive prevention: a captured frame must never mask a runtime access violation."""
import json
from fidelity_legacy_launcher_bridge_v3 import clean_diagnostic_capture
good={"diagnostic_capture_status":"PASS","capture_integrity":"PASS","exit_code":0,
      "failure_reason":"DIAGNOSTIC_COMPLETE_NOT_FIDELITY_VERIFIED"}
receipt={"status":"BLOCKED"}
assert clean_diagnostic_capture(good,receipt)
for code in (None,1,3221225477,-1073741819):
 bad=dict(good,exit_code=code)
 assert not clean_diagnostic_capture(bad,receipt),code
for status in ("CAPTURE_PASS_RUNTIME_EXIT_NOT_CLEAN","CAPTURE_PENDING"):
 assert not clean_diagnostic_capture(dict(good,diagnostic_capture_status=status),receipt)
assert not clean_diagnostic_capture(dict(good,failure_reason="DIAGNOSTIC_RUNTIME_NOT_CLEANLY_CLOSED"),receipt)
assert not clean_diagnostic_capture(good,{"status":"PASS"})
print(json.dumps({"schema":"OpenRemaster.DiagnosticCrashFailClosedCanary.v3","status":"PASS",
                  "crash_exit_codes_rejected":[1,3221225477,-1073741819],
                  "fidelity_promotion":"NEVER_BY_DIAGNOSTIC"}))
