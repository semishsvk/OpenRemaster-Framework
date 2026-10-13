"""Copy existing proven v1 capture schedule into a NEW explicitly-versioned passive-only
bounded 75-second v2 schedule contract. Never mutate frozen v1 for existing runs.
"""
from pathlib import Path
import hashlib,json
cp=Path(__file__).resolve().parent
source=cp/"fidelity_capture_sequence_v1.py"
destination=cp/"fidelity_capture_sequence_v2.py"
assert source.is_file() and not destination.exists()
text=source.read_text(encoding="utf-8")
changes=[
 ("def validate_capture_schedule(schedule,mode=", "def validate_capture_schedule_v2(schedule,mode="),
 ("def acquire_bound_wgc_sequence(capture_dir,", "def acquire_bound_wgc_sequence_v2(capture_dir,"),
 ("def verify_bounded_wgc_sequence(base,", "def verify_bounded_wgc_sequence_v2(base,"),
 ("validate_capture_schedule(", "validate_capture_schedule_v2("),
 ("44.0", "75.0"),
 ("OpenRemaster.BoundedFrameSchedule.v1", "OpenRemaster.BoundedFrameSchedule.v2"),
 ("OpenRemaster.BoundedFrameScheduleVerification.v1", "OpenRemaster.BoundedFrameScheduleVerification.v2")
]
for old,new in changes:
 assert old in text,(old,new)
 text=text.replace(old,new)
text='"""Version 2 extended passive-only camera observation, copied from v1 with larger explicit bound.\nDoes NOT change v1 contracts or assert fidelity. Source below remains mechanically identical except version/name/horizon.\n"""\n'+text
destination.write_text(text,encoding="utf-8")
report={"schema":"OpenRemaster.ExtendedCaptureScheduleBuild.v1",
"status":"CREATED_V2_V1_UNCHANGED","source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
"v2_sha256":hashlib.sha256(destination.read_bytes()).hexdigest(),
"max_time_seconds":75,"v1_horizon":44,"max_frames":5,
"mode":"passive_diagnostic_only","fidelity_acceptance":"NOT_AUTHORIZED"}
out=cp/"fidelity_capture_schedule_v2_build_evidence.json"
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report))
