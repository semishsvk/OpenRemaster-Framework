import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
src=Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json")
job=json.loads(src.read_text(encoding="utf-8"))
job["job_id"]="native-route-canary-20261008"
job["task"]="NativeLocalQueue route verification"
q=root/"queue"
f=q/"pending"/(job["job_id"]+".json")
if any((q/d/f.name).exists() for d in ("pending","running","done","failed")):raise RuntimeError("JOB_ALREADY_EXISTS")
f.write_text(json.dumps(job,indent=2),encoding="utf-8")
p=subprocess.run([sys.executable,str(root/"agent.py"),"--once"],capture_output=True,text=True,timeout=180)
receipt=Path(r"F:\Remaster Framework\runtime-test\results")/job["job_id"]/"control-receipt.json"
data=json.loads(receipt.read_text()) if receipt.exists() else {}
ok=p.returncode==0 and data.get("status")=="PASS" and data.get("worker",{}).get("adapter")=="NativeLocalQueue"
print(json.dumps({"schema":"NativeRoutingCanary.v1","status":"PASS" if ok else "FAIL","adapter":data.get("worker",{}).get("adapter"),"acceptance":data.get("acceptance_status")},indent=2))
sys.exit(0 if ok else 1)
