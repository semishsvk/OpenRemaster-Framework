import json,hashlib,hmac,time,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
QUEUE=ROOT/"queue"
WORK=ROOT.parent.parent/"work"
ALLOWED={"OpenAzrael":"scripts/kg001_headless_runner_v109.gd"}
def validate_envelope(envelope,key,now=None):
 if not isinstance(envelope,dict):return "INVALID_SCHEMA"
 if now is None:now=int(time.time())
 if envelope.get("schema")!="NativeJobEnvelope.v1":return "INVALID_SCHEMA"
 if envelope.get("audience")!="HomePC-NativeWorker":return "INVALID_AUDIENCE"
 try:timestamp=int(envelope.get("timestamp",0))
 except (TypeError,ValueError):return "INVALID_TIMESTAMP"
 if abs(now-timestamp)>120:return "EXPIRED"
 job=envelope.get("job")
 if not isinstance(job,dict) or job.get("schema")!="ORCH-K003.Job.v1":return "INVALID_JOB"
 jid=job.get("job_id")
 if not isinstance(jid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,96}",jid):return "INVALID_JOB_ID"
 ex=job.get("execution")
 if not isinstance(ex,dict) or ex.get("kind")!="godot_runtime":return "DISALLOWED_EXECUTION"
 project=job.get("project")
 if project not in ALLOWED:return "PROJECT_NOT_ALLOWLISTED"
 path=ex.get("project_path")
 if not isinstance(path,str):return "INVALID_PROJECT_PATH"
 try:
  resolved=Path(path).resolve(strict=True)
  expected=(WORK/project).resolve(strict=True)
  if resolved!=expected or not (resolved/"project.godot").is_file():return "INVALID_PROJECT_PATH"
 except (OSError,ValueError):return "INVALID_PROJECT_PATH"
 if ex.get("mode")!="replay" or ex.get("args")!=["--script","res://"+ALLOWED[project]]:return "DISALLOWED_ARGUMENTS"
 if job.get("required_capabilities")!=["filesystem.read","process.exec","godot.4.7.2","godot.headless","runtime.replay"]:return "INVALID_CAPABILITIES"
 if job.get("validation")!={"expected_exit_code":0}:return "INVALID_VALIDATION"
 if not isinstance(key,bytes) or len(key)<32:return "INVALID_KEY"
 payload=json.dumps({k:v for k,v in envelope.items() if k!="mac"},sort_keys=True,separators=(",",":")).encode()
 expected=hmac.new(key,payload,hashlib.sha256).hexdigest()
 if not hmac.compare_digest(expected,str(envelope.get("mac",""))):return "BAD_MAC"
 if any((QUEUE/d/(jid+".json")).exists() for d in ("pending","running","done","failed")):return "REPLAY_OR_DUPLICATE"
 return "PASS"
