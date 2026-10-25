import json,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
queue=root/"queue"
for n in ("pending","running","done","failed"): (queue/n).mkdir(parents=True,exist_ok=True)
src=Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json")
job=json.loads(src.read_text(encoding="utf-8"))
job["job_id"]="native-worker-azrael-smoke-20261008"
job["task"]="NativeWorker transport-independent ORCH smoke"
out=queue/"pending"/(job["job_id"]+".json")
out.write_text(json.dumps(job,indent=2),encoding="utf-8")
r=subprocess.run([sys.executable,str(root/"agent.py"),"--once"],capture_output=True,text=True,timeout=240)
receipt=queue/"done"/(job["job_id"]+".receipt.json")
result={"agent_exit":r.returncode,"receipt_exists":receipt.exists(),"agent_stderr":r.stderr[-1000:]}
if receipt.exists():result["receipt"]=json.loads(receipt.read_text(encoding="utf-8"))
print(json.dumps(result,indent=2))
sys.exit(0 if receipt.exists() and result["receipt"]["returncode"]==0 else 1)
