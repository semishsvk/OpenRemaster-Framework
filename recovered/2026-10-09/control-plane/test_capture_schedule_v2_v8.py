"""v1 backward-compatible and v2 late-frame negative canaries with no runtime launch."""
import ast,json
from pathlib import Path
from fidelity_capture_sequence_v1 import validate_capture_schedule
from fidelity_capture_sequence_v2 import validate_capture_schedule_v2
from fidelity_runtime_isolation_v1 import IsolationError,sha256
CP=Path(__file__).resolve().parent
def expect(reason,call):
 try:call()
 except IsolationError as e:
  assert e.reason==reason,(reason,e.reason);return
 raise AssertionError("SCHEDULE_GATE_FAIL_OPEN "+reason)
assert validate_capture_schedule([3,8,14])==[3.,8.,14.]
expect("CAPTURE_SCHEDULE_UNSAFE_OFFSET",lambda:validate_capture_schedule([37,60]))
assert validate_capture_schedule_v2([37,42,55,70])==[37.,42.,55.,70.]
expect("CAPTURE_SEQUENCE_REQUIRES_PASSIVE_DIAGNOSTIC",
       lambda:validate_capture_schedule_v2([37,55],"strict_fidelity"))
expect("CAPTURE_SCHEDULE_UNSAFE_OFFSET",lambda:validate_capture_schedule_v2([65,75.01]))
expect("CAPTURE_SCHEDULE_UNSAFE_OFFSET",lambda:validate_capture_schedule_v2([42,43]))
schema=json.loads((CP/"schemas"/"orch-k003-job.schema.json").read_text(encoding="utf-8-sig"))
assert "v2_extended" in schema["properties"]["execution"]["properties"]["capture_schedule_contract"]["enum"]
for p in [CP/"fidelity_capture_sequence_v2.py",CP/"fidelity_runtime_worker_v1.py",CP/"orch_k003.py"]:
 ast.parse(p.read_text(encoding="utf-8-sig"),filename=str(p))
print(json.dumps({"schema":"OpenRemaster.BoundedCaptureScheduleV2Canary.v1",
 "status":"PASS","previous_v1_max":44,"extended_v2_max":75,
 "accepted_extended":[37,42,55,70],
 "v1_unchanged":sha256(CP/"fidelity_capture_sequence_v1.py")=="721a5254c761b430d5e754ce81b9d55f31bb4c6967e9664a443350b6866a2dd7",
 "no_gui_launched":True,"fidelity_accepted":False}))
