import json,os,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
FRAMEWORK=ROOT.parent.parent
QUEUE=ROOT/"queue"
for n in ("pending","running","done","failed"): (QUEUE/n).mkdir(parents=True,exist_ok=True)
CONTROL=FRAMEWORK/"orchestrator"/"control-plane"/"orch_k003.py"
def run_once():
 for f in sorted((QUEUE/"pending").glob("*.json")):
  try:
   job=json.loads(f.read_text(encoding="utf-8"))
   if job.get("schema")!="ORCH-K003.Job.v1" or not job.get("job_id") or f.stem!=job["job_id"]: raise ValueError("INVALID_JOB")
   kind=job.get("execution",{}).get("kind")
   if kind not in ("godot_runtime","fidelity_runtime"): raise ValueError("EXECUTION_NOT_ALLOWLISTED")
   if kind=="godot_runtime":
    if job["execution"].get("mode","replay") not in ("smoke","headless","replay","import"): raise ValueError("INTERACTIVE_GODOT_REQUIRES_FIDELITY_SUPERVISOR")
    project=Path(job["execution"]["project_path"]).resolve()
    if not project.is_relative_to((FRAMEWORK/"work").resolve()) or not (project/"project.godot").is_file(): raise ValueError("INVALID_PROJECT_PATH")
   else:
    ex=job["execution"]
    exe=Path(ex["executable"]).resolve()
    roots=((FRAMEWORK/"source").resolve(),(FRAMEWORK/"work").resolve())
    if not exe.is_file() or not any(exe.is_relative_to(root) for root in roots): raise ValueError("INVALID_FIDELITY_EXECUTABLE_PATH")
    if "runtime.fidelity_isolated" not in job.get("required_capabilities",[]): raise ValueError("FIDELITY_CAPABILITY_REQUIRED")
   running=QUEUE/"running"/f.name
   f.rename(running)
   proc=subprocess.run([sys.executable,str(CONTROL),str(running)],capture_output=True,text=True,timeout=300)
   result={"job_id":job["job_id"],"returncode":proc.returncode,"stdout":proc.stdout[-8000:],"stderr":proc.stderr[-4000:]}
   target=QUEUE/("done" if proc.returncode==0 else "failed")
   (target/(f.stem+".receipt.json")).write_text(json.dumps(result,indent=2),encoding="utf-8")
   running.rename(target/f.name)
  except Exception as e:
   (QUEUE/"failed"/(f.stem+".error.json")).write_text(json.dumps({"error":str(e),"type":type(e).__name__}),encoding="utf-8")
   if f.exists(): f.rename(QUEUE/"failed"/f.name)
def main():
 if "--once" in sys.argv: run_once();return
 while True: run_once();time.sleep(5)
if __name__=="__main__": main()
