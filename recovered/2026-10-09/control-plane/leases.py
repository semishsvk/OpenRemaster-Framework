import json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path

def now(): return datetime.now(timezone.utc)

def acquire(path, job_id, worker_id, attempt_id, ttl_seconds=60):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_file():
        old=json.loads(p.read_text(encoding="utf-8-sig"))
        exp=datetime.fromisoformat(old["expires_at"])
        if exp > now():
            return {"status":"BUSY","lease":old}
    lease={"schema":"WorkerLease.v1","job_id":job_id,"worker_id":worker_id,"attempt_id":attempt_id,
           "acquired_at":now().isoformat(),"expires_at":(now()+timedelta(seconds=ttl_seconds)).isoformat()}
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(lease,indent=2),encoding="utf-8")
    os.replace(tmp,p)
    return {"status":"ACQUIRED","lease":lease}

def renew(path, attempt_id, ttl_seconds=60):
    p=Path(path)
    if not p.is_file(): return {"status":"MISSING"}
    lease=json.loads(p.read_text(encoding="utf-8-sig"))
    if lease.get("attempt_id")!=attempt_id: return {"status":"REJECTED","reason":"ATTEMPT_MISMATCH","lease":lease}
    lease["expires_at"]=(now()+timedelta(seconds=ttl_seconds)).isoformat()
    tmp=p.with_suffix(p.suffix+".tmp"); tmp.write_text(json.dumps(lease,indent=2),encoding="utf-8"); os.replace(tmp,p)
    return {"status":"RENEWED","lease":lease}

def inspect(path):
    p=Path(path)
    if not p.is_file(): return {"status":"MISSING"}
    lease=json.loads(p.read_text(encoding="utf-8-sig"))
    return {"status":"EXPIRED" if datetime.fromisoformat(lease["expires_at"]) <= now() else "ACTIVE","lease":lease}

def release(path, attempt_id):
    p=Path(path)
    if not p.is_file(): return False
    lease=json.loads(p.read_text(encoding="utf-8-sig"))
    if lease.get("attempt_id")!=attempt_id: return False
    p.unlink(); return True
