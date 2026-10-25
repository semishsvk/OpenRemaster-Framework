import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
QUEUE=ROOT/"queue"
def recover():
 (QUEUE/"pending").mkdir(parents=True,exist_ok=True)
 (QUEUE/"failed").mkdir(parents=True,exist_ok=True)
 report=[]
 for f in sorted((QUEUE/"running").glob("*.json")):
  try:
   job=json.loads(f.read_text(encoding="utf-8"))
   jid=job.get("job_id",f.stem)
   result=ROOT.parent.parent/"runtime-test"/"results"/jid
   receipt=result/"control-receipt.json"
   if receipt.exists():
    data=json.loads(receipt.read_text(encoding="utf-8"))
    if data.get("job_id")==jid and data.get("status") in ("PASS","FAIL","BLOCKED"):
     dest=QUEUE/("done" if data["status"]=="PASS" else "failed")
     dest.mkdir(exist_ok=True)
     f.rename(dest/f.name)
     report.append({"job_id":jid,"action":"RECONCILED","status":data["status"]})
     continue
   dest=QUEUE/"failed"/f.name
   f.rename(dest)
   (QUEUE/"failed"/(jid+".recovery.json")).write_text(json.dumps({"status":"BLOCKED","reason":"EXECUTION_OUTCOME_UNKNOWN_RECONCILE_REQUIRED"},indent=2))
   report.append({"job_id":jid,"action":"BLOCKED_UNKNOWN_OUTCOME"})
  except Exception as e:report.append({"file":f.name,"error":str(e)})
 print(json.dumps({"schema":"NativeWorkerRecovery.v1","jobs":report},indent=2))
if __name__=="__main__":recover()
