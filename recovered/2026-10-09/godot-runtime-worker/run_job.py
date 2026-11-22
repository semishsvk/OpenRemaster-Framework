import argparse, datetime, hashlib, json, platform, subprocess, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/"config"/"worker.json").read_text(encoding="utf-8"))

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def run(job):
    project=Path(job["project_path"]); pg=project/"project.godot"
    godot=Path(CFG["godot_console"])
    if not pg.is_file(): raise FileNotFoundError(f"project.godot missing: {pg}")
    if not godot.is_file(): raise FileNotFoundError(f"Godot missing: {godot}")
    outroot=Path(CFG["runtime_root"])/"results"/job["job_id"]; outroot.mkdir(parents=True,exist_ok=True)
    mode=job.get("mode","smoke"); cmd=[str(godot),"--path",str(project)]
    if mode in ("smoke","headless","replay","import"): cmd += ["--headless"]
    if mode=="import": cmd += ["--editor","--quit"]
    cmd += job.get("args",[])
    started=now(); t0=time.time()
    with open(outroot/"stdout.log","w",encoding="utf-8") as so, open(outroot/"stderr.log","w",encoding="utf-8") as se:
        proc=subprocess.run(cmd,stdout=so,stderr=se,text=True,timeout=job.get("timeout_seconds",CFG["default_timeout_seconds"]))
    fingerprint={
      "schema":"ExecutionEnvironmentFingerprint.v1","captured_at":now(),"machine":platform.node(),
      "os":platform.platform(),"python":platform.python_version(),"godot_version":CFG["expected_version"],
      "godot_sha256":sha256(godot),"project_godot_sha256":sha256(pg),
      "capture_authority":CFG["capture_authority"],"remote_desktop_capture_authority":False
    }
    expected=job.get("expected_exit_code",0); status="PASS" if proc.returncode==expected else "FAIL"
    result={"schema":"GodotRuntimeResult.v1","job_id":job["job_id"],"project":job["project"],"mode":mode,
      "status":status,"exit_code":proc.returncode,"expected_exit_code":expected,"operation_id":job.get("operation_id"),"started_at":started,
      "finished_at":now(),"duration_seconds":round(time.time()-t0,3),"command":cmd,"fingerprint":fingerprint,
      "stdout_sha256":sha256(outroot/"stdout.log"),"stderr_sha256":sha256(outroot/"stderr.log")}
    (outroot/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (outroot/"fingerprint.json").write_text(json.dumps(fingerprint,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2)); return 0 if status=="PASS" else 1

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("job"); a=ap.parse_args()
    job=json.loads(Path(a.job).read_text(encoding="utf-8"))
    if job.get("schema")!="GodotRuntimeJob.v1": raise ValueError("Unsupported job schema")
    return run(job)

if __name__=="__main__":
    try: sys.exit(main())
    except subprocess.TimeoutExpired as e: print(f"TIMEOUT: {e}",file=sys.stderr); sys.exit(124)
    except Exception as e: print(f"ERROR: {type(e).__name__}: {e}",file=sys.stderr); sys.exit(2)
