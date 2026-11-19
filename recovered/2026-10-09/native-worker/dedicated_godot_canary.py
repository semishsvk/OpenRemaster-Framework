import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
queue=root/"queue"
job_path=Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json")
job=json.loads(job_path.read_text(encoding="utf-8"))
job["job_id"]="native-dedicated-azrael-20261008"
job["task"]="Dedicated identity Godot E2E canary"
pending=queue/"pending"/(job["job_id"]+".json")
if pending.exists() or (queue/"done"/pending.name).exists():raise RuntimeError("CANARY_ALREADY_EXISTS")
pending.write_text(json.dumps(job,indent=2),encoding="utf-8")
p=subprocess.run([sys.executable,str(root/"agent.py"),"--once"],capture_output=True,text=True,timeout=240)
receipt=queue/"done"/(job["job_id"]+".receipt.json")
result={"schema":"DedicatedGodotCanary.v1","agent_exit":p.returncode,"receipt_exists":receipt.exists(),"stderr":p.stderr[-1200:]}
if receipt.exists():
 data=json.loads(receipt.read_text(encoding="utf-8"))
 result["orchestrator_exit"]=data.get("returncode")
 result["orchestrator_receipt"]=data.get("stdout","")[-3500:]
out=queue/"done"/"dedicated-godot-canary-result.json"
out.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
sys.exit(0 if receipt.exists() and result.get("orchestrator_exit")==0 else 1)
