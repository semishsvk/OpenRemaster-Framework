import json,subprocess,sys,uuid
from pathlib import Path
root=Path(__file__).resolve().parent
q=root/"queue"
cases=[
 ("invalid-kind",{"schema":"ORCH-K003.Job.v1","execution":{"kind":"executable_runtime"}},"EXECUTION_NOT_ALLOWLISTED"),
 ("outside-project",{"schema":"ORCH-K003.Job.v1","execution":{"kind":"godot_runtime","project_path":r"C:\Windows"}},"INVALID_PROJECT_PATH"),
 ("invalid-schema",{"schema":"UNKNOWN","execution":{"kind":"godot_runtime"}},"INVALID_JOB")
]
rows=[]
for label,job,reason in cases:
 jid="native-negative-"+label+"-"+uuid.uuid4().hex[:8]
 job.update(job_id=jid,project="OpenAzrael",task="negative test",inputs=[],required_capabilities=[],validation={"expected_exit_code":0})
 (q/"pending"/(jid+".json")).write_text(json.dumps(job),encoding="utf-8")
 p=subprocess.run([sys.executable,str(root/"agent.py"),"--once"],capture_output=True,text=True,timeout=30)
 ep=q/"failed"/(jid+".error.json")
 result=json.loads(ep.read_text()) if ep.exists() else {}
 ok=p.returncode==0 and result.get("error")==reason and (q/"failed"/(jid+".json")).exists()
 rows.append({"case":label,"status":"PASS" if ok else "FAIL","observed":result.get("error")})
print(json.dumps({"schema":"NativeWorkerNegativeCanary.v1","status":"PASS" if all(r["status"]=="PASS" for r in rows) else "FAIL","cases":rows},indent=2))
sys.exit(0 if all(r["status"]=="PASS" for r in rows) else 1)
