import json,subprocess,sys,uuid
from pathlib import Path
root=Path(__file__).resolve().parent
q=root/"queue"
jid="native-recovery-"+uuid.uuid4().hex[:10]
f=q/"running"/(jid+".json")
f.write_text(json.dumps({"schema":"ORCH-K003.Job.v1","job_id":jid}),encoding="utf-8")
p=subprocess.run([sys.executable,str(root/"recover.py")],capture_output=True,text=True,timeout=30)
marker=q/"failed"/(jid+".recovery.json")
out=json.loads(marker.read_text()) if marker.exists() else {}
ok=p.returncode==0 and out.get("reason")=="EXECUTION_OUTCOME_UNKNOWN_RECONCILE_REQUIRED" and (q/"failed"/f.name).exists()
print(json.dumps({"schema":"NativeWorkerRecoveryNegativeCanary.v1","status":"PASS" if ok else "FAIL","reason":out.get("reason")},indent=2))
sys.exit(0 if ok else 1)
