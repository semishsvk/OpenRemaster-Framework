import json,subprocess,sys,time,datetime,os
from pathlib import Path
root=Path(__file__).resolve().parent
q=root/"queue"
py=root/"runtime"/"python.exe"
p=subprocess.Popen([str(py),str(root/"service_entry.py")],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
samples=[]
try:
 for _ in range(3):
  time.sleep(6)
  h=json.loads((q/"worker-heartbeat.json").read_text(encoding="utf-8"))
  samples.append(h)
 ok=p.poll() is None and len({s["utc"] for s in samples})==3 and all(s["state"] in ("IDLE","RUNNING") for s in samples)
 print(json.dumps({"schema":"NativeWorkerLongRunCanary.v1","status":"PASS" if ok else "FAIL","samples":samples,"pid":p.pid},indent=2))
finally:
 p.terminate()
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.kill();p.wait()
