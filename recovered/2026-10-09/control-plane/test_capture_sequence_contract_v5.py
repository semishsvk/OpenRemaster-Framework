"""Synthetic technical attestation and negative admission for multi-frame capture.
No game runtime, keyboard, screenshot from desktop or audio device is launched.
"""
import json,subprocess,sys,tempfile,uuid
from pathlib import Path
from fidelity_capture_sequence_v1 import validate_capture_schedule,verify_bounded_wgc_sequence
from fidelity_runtime_isolation_v1 import IsolationError,sha256
root=Path(__file__).resolve().parents[2]
cp=Path(__file__).resolve().parent
def reject(reason,call):
 try:call()
 except IsolationError as e:
  assert e.reason==reason,(reason,e.reason);return
 raise AssertionError("FAIL_OPEN_EXPECTED "+reason)
assert validate_capture_schedule([2,8,18,42])==[2.0,8.0,18.0,42.0]
reject("CAPTURE_SCHEDULE_LENGTH_INVALID",lambda:validate_capture_schedule([8]))
reject("CAPTURE_SCHEDULE_UNSAFE_OFFSET",lambda:validate_capture_schedule([2,3]))
reject("CAPTURE_SCHEDULE_UNSAFE_OFFSET",lambda:validate_capture_schedule([3,46]))
reject("CAPTURE_SEQUENCE_REQUIRES_PASSIVE_DIAGNOSTIC",lambda:validate_capture_schedule([3,12],"strict_fidelity"))
reject("CAPTURE_SCHEDULE_NONNUMERIC",lambda:validate_capture_schedule([2,"9"]))
with tempfile.TemporaryDirectory(prefix="fidelity-sequence-canary-",dir=root/"runtime-test"/"results") as tmp:
 base=Path(tmp)
 rows=[]
 for i,at in enumerate([3,10],1):
  dest=base/"samples"/("point-%02d"%i)
  dest.mkdir(parents=True)
  frame=dest/"frame-0001.bmp"
  frame.write_bytes(b"TECHNICAL_TEST_ONLY_FRAME_BYTES"+bytes([i])*128)
  sample={"schema":"FidelityLocalCaptureAttestation.v1","backend":"windows_graphics_capture",
          "remote_desktop_capture_authority":False,
          "run_token":"fixture-token","pid":1515,"creation_ticks_100ns":12345678,
          "hwnd":2020,"executable_sha256":"fixture-exe",
          "frames":[{"path":"frame-0001.bmp","sha256":sha256(frame)}]}
  mf=dest/"capture-attestation.json"
  mf.write_text(json.dumps(sample))
  rows.append({"path":str(frame.relative_to(base)).replace("\\","/"),
               "sha256":sha256(frame),
               "sample_index":i,"requested_at_seconds":at,"started_at_seconds":at+0.04,
               "sample_manifest_path":str(mf.relative_to(base)).replace("\\","/"),
               "sample_manifest_sha256":sha256(mf)})
 master={"schema":"FidelityLocalCaptureAttestation.v1",
         "capture_schedule_schema":"OpenRemaster.BoundedFrameSchedule.v1",
         "backend":"windows_graphics_capture","remote_desktop_capture_authority":False,
         "run_token":"fixture-token","pid":1515,"creation_ticks_100ns":12345678,
         "hwnd":2020,"executable_sha256":"fixture-exe","frames":rows}
 assert verify_bounded_wgc_sequence(base,master)["verified_frames"]==2
 sample_manifest=base/rows[0]["sample_manifest_path"]
 v=json.loads(sample_manifest.read_text())
 v["hwnd"]=555
 sample_manifest.write_text(json.dumps(v))
 rows[0]["sample_manifest_sha256"]=sha256(sample_manifest)
 reject("CAPTURE_SEQUENCE_SAMPLE_OWNER_MISMATCH",lambda:verify_bounded_wgc_sequence(base,master))
 v["hwnd"]=2020
 sample_manifest.write_text(json.dumps(v))
 rows[0]["sample_manifest_sha256"]=sha256(sample_manifest)
 f=base/rows[1]["path"]
 f.write_bytes(b"TAMPERED")
 reject("CAPTURE_SEQUENCE_NATIVE_FRAME_TAMPERED",lambda:verify_bounded_wgc_sequence(base,master))

rid="fidelity-sequence-negative-"+uuid.uuid4().hex[:9]
exe=root/"source"/"Zork Nemesis"/"DOSBOX"/"DOSBox.exe"
job={"schema":"ORCH-K003.Job.v1","job_id":rid,"project":"OpenZork","task":"NegativeSequenceAdmission",
     "required_capabilities":["runtime.fidelity_isolated"],"inputs":[],
     "execution":{"kind":"fidelity_runtime","capture_mode":"strict_fidelity",
                  "runtime_kind":"dosbox","executable":str(exe),
                  "capture_schedule_seconds":[4,9]},
     "validation":{"expected_exit_code":0}}
inp=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(rid+".json")
inp.parent.mkdir(exist_ok=True,parents=True)
inp.write_text(json.dumps(job))
p=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(inp)],
                 capture_output=True,text=True,timeout=15)
out=root/"runtime-test"/"results"/rid
receipt=json.loads((out/"control-receipt.json").read_text())
assert p.returncode==2 and receipt["reason"]=="CAPTURE_SEQUENCE_REQUIRES_PASSIVE_DIAGNOSTIC"
assert not (out/"result.json").exists()
print(json.dumps({"schema":"OpenRemaster.CaptureSequenceContractCanary.v1",
                  "status":"PASS","validated_schedule":[2,8,18,42],
                  "synthetic_manifest_provenance":"PASS",
                  "tampered_frame_rejected":True,
                  "wrong_pid_hwnd_rejected":True,
                  "strict_fidelity_sequence_blocked":True,"original_game_launches":0}))
