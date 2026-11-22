import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
tests=["test_execution_journal.py","test_recovery.py","test_idempotency.py","test_leases.py","test_heartbeat.py","test_process_crash.py","test_corrupt_artifact.py","test_corrupt_checkpoint.py","test_double_rehydration.py","test_negative_validation.py"]
results=[]
for test in tests:
    p=subprocess.run([sys.executable,str(ROOT/test)],capture_output=True,text=True)
    results.append({"test":test,"exit_code":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip(),
                    "status":"PASS" if p.returncode==0 else "FAIL"})
status="PASS" if all(r["status"]=="PASS" for r in results) else "FAIL"
report={"schema":"ORCH-K003.CommissioningSuite.v1","status":status,"results":results,
        "external_blockers":["DEDICATED_WORKER_IDENTITY_AND_CORPUS_READ_ONLY_ACL"]}
out=ROOT.parent.parent/"runtime-test"/"results"/"orch-commissioning-suite.json"
out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
raise SystemExit(0 if status=="PASS" else 1)
