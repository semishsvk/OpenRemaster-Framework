import json,subprocess,sys,time,getpass
from pathlib import Path
root=Path(__file__).resolve().parent
q=root/"queue"
p=subprocess.Popen([str(root/"runtime"/"python.exe"),str(root/"service_entry.py")],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 time.sleep(11)
 hb=json.loads((q/"worker-heartbeat.json").read_text(encoding="utf-8"))
 ok=p.poll() is None and hb.get("pid")==p.pid and hb.get("state") in ("IDLE","RUNNING") and getpass.getuser().lower()=="openremasterworker"
 result={"schema":"DedicatedLongRunCanary.v1","status":"PASS" if ok else "FAIL","identity":getpass.getuser(),"pid":p.pid,"heartbeat":hb}
finally:
 p.terminate()
 try:p.wait(timeout=8)
 except subprocess.TimeoutExpired:p.kill();p.wait()
(q/"done"/"dedicated-longrun-canary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
sys.exit(0 if ok else 1)
