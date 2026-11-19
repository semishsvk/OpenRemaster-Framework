import json,os,subprocess,sys,time,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
QUEUE=ROOT/"queue"
HEARTBEAT=QUEUE/"worker-heartbeat.json"
def heartbeat(state):
 payload={"schema":"NativeWorkerHeartbeat.v1","worker":"HomePC-NativeWorker","pid":os.getpid(),"state":state,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 tmp=HEARTBEAT.with_suffix(".tmp")
 tmp.write_text(json.dumps(payload,indent=2),encoding="utf-8")
 os.replace(tmp,HEARTBEAT)
def main():
 heartbeat("STARTING")
 recovery=subprocess.run([sys.executable,str(ROOT/"recover.py")],capture_output=True,text=True,timeout=30)
 if recovery.returncode:raise RuntimeError("RECOVERY_FAILED")
 import agent
 if "--once" in sys.argv:
  heartbeat("RUNNING");agent.run_once();heartbeat("STOPPED");return
 while True:
  heartbeat("RUNNING");agent.run_once();heartbeat("IDLE");time.sleep(5)
if __name__=="__main__":main()
