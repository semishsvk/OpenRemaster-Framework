import json,hmac,hashlib,time,secrets,urllib.request,urllib.error,sys
from pathlib import Path
root=Path(__file__).resolve().parent
job=json.loads(Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json").read_text())
job["job_id"]="remote-signed-godot-20261008"
job["task"]="Tailnet signed Godot E2E canary"
envelope={"schema":"NativeJobEnvelope.v1","audience":"HomePC-NativeWorker","timestamp":int(time.time()),"nonce":secrets.token_hex(16),"job":job}
key=(root/"secrets"/"transport.key").read_bytes()
assert len(key)==32
payload=json.dumps(envelope,sort_keys=True,separators=(",",":")).encode()
envelope["mac"]=hmac.new(key,payload,hashlib.sha256).hexdigest()
req=urllib.request.Request("https://homepc.tail14e835.ts.net:8443/v1/jobs",data=json.dumps(envelope).encode(),headers={"Content-Type":"application/json"},method="POST")
try:
 with urllib.request.urlopen(req,timeout=10) as r:code=r.status;body=json.loads(r.read())
except urllib.error.HTTPError as e:code=e.code;body=json.loads(e.read())
print(json.dumps({"schema":"RemoteSignedSubmission.v1","http_status":code,"response":body},indent=2))
sys.exit(0 if code==202 else 1)
