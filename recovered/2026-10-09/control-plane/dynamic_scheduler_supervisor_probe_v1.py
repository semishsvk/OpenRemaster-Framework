"""Isolated local process supervisor probe; NOT a production ORCH-K003 dispatcher.
Runs only an explicitly hashed Python fixture in a private temporary directory.
"""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute_fixture(script,expected_sha256,workdir,timeout_seconds=5):
    script=Path(script).resolve(strict=True);workdir=Path(workdir).resolve(strict=True)
    if script.parent!=workdir or script.suffix.lower()!=".py":
        return {"status":"BLOCKED","reason":"OUTSIDE_ISOLATED_WORKDIR"}
    if not 0.1<=timeout_seconds<=15:return {"status":"BLOCKED","reason":"TIMEOUT_BUDGET"}
    if sha(script)!=expected_sha256:return {"status":"BLOCKED","reason":"SOURCE_HASH_MISMATCH"}
    start=time.monotonic();start_wall=time.time()
    proc=subprocess.Popen([sys.executable,"-B",str(script)],cwd=workdir,
                          stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,text=True,
                          env={"PATH":os.environ.get("PATH",""),
                               "SYSTEMROOT":os.environ.get("SYSTEMROOT",""),
                               "PYTHONDONTWRITEBYTECODE":"1"})
    timed_out=False
    try:out,err=proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out=True;proc.kill();out,err=proc.communicate(timeout=3)
    stopped=proc.poll() is not None
    if not stopped:return {"status":"BLOCKED","reason":"PROCESS_NOT_RECONCILED","pid":proc.pid}
    return {"status":"BLOCKED" if timed_out else ("PASS" if proc.returncode==0 else "FAIL"),
            "pid":proc.pid,"exit_code":proc.returncode,"timed_out":timed_out,
            "started_wall_epoch":start_wall,"elapsed_monotonic_seconds":time.monotonic()-start,
            "process_stopped_verified":stopped,"stdout_sha256":hashlib.sha256(out.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(err.encode()).hexdigest(),
            "script_sha256":sha(script),"native_game_executed":False}
