"""Synthetic child only: Job Object closure kills its owned process, leaves unrelated child alone."""
from datetime import datetime,timezone
from pathlib import Path
import ctypes,json,subprocess,sys,time
from fidelity_runtime_worker_v1 import attach_job_object,K

def make_child():
    return subprocess.Popen([sys.executable,"-B","-c","import time;time.sleep(30)"],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
owned,unrelated=None,None
try:
    owned=make_child()
    unrelated=make_child()
    assert owned.poll() is None and unrelated.poll() is None
    job=attach_job_object(owned)
    assert owned.poll() is None and unrelated.poll() is None
    K.CloseHandle(job)
    owned.wait(timeout=7)
    assert owned.poll() is not None
    assert unrelated.poll() is None, "Unrelated child unexpectedly terminated"
    report={"schema":"OpenRemaster.JobObjectOwnershipCanary.v1","status":"PASS",
           "owned_pid":owned.pid,"owned_terminated_on_job_close":True,
           "unrelated_pid":unrelated.pid,"unrelated_survived":True,
           "original_game_processes_touched":0}
    dest=Path(__file__).resolve().parents[2]/"runtime-test"/"results"/"fidelity-job-object-canary-20261009.json"
    dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(dict(report,evidence_path=str(dest))))
finally:
    for p in (owned,unrelated):
        if p:
            if p.poll() is None:
                p.terminate()
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill();p.wait(timeout=3)
