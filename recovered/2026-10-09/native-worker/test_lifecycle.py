import json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
q=root/"queue"
p=subprocess.Popen([str(root/"runtime"/"python.exe"),str(root/"service_entry.py")],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 time.sleep(12)
 hb=json.loads((q/"worker-heartbeat.json").read_text(encoding="utf-8"))
 ok=p.poll() is None and hb["pid"]==p.pid and hb["state"] in ("IDLE","RUNNING")
 print(json.dumps({"schema":"NativeWorkerLifecycleCanary.v1","status":"PASS" if ok else "FAIL","pid":p.pid,"heartbeat":hb},indent=2))
finally:
 p.terminate()
 try:p.wait(timeout=8)
 except subprocess.TimeoutExpired:p.kill();p.wait()
sys.exit(0 if ok else 1)
