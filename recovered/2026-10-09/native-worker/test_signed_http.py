import json,hmac,hashlib,time,threading,urllib.request,urllib.error,tempfile,secrets
from pathlib import Path
from http.server import ThreadingHTTPServer
import gateway
root=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix="native-http-canary-") as tmp:
 base=Path(tmp);(base/"pending").mkdir();(base/"running").mkdir();(base/"done").mkdir();(base/"failed").mkdir()
 key=secrets.token_bytes(32);keyfile=base/"test.key";keyfile.write_bytes(key)
 gateway.QUEUE=base;gateway.KEYFILE=keyfile
 import transport_contract
 transport_contract.QUEUE=base
 job=json.loads(Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json").read_text())
 job["job_id"]="signed-http-canary-20261008"
 env={"schema":"NativeJobEnvelope.v1","audience":"HomePC-NativeWorker","timestamp":int(time.time()),"nonce":secrets.token_hex(16),"job":job}
 raw=json.dumps(env,sort_keys=True,separators=(",",":")).encode()
 env["mac"]=hmac.new(key,raw,hashlib.sha256).hexdigest()
 server=ThreadingHTTPServer(("127.0.0.1",0),gateway.Handler)
 t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
 def post(obj):
  data=json.dumps(obj).encode()
  req=urllib.request.Request("http://127.0.0.1:"+str(server.server_port)+"/v1/jobs",data=data,method="POST")
  try:
   with urllib.request.urlopen(req,timeout=4) as r:return r.status,json.loads(r.read())
  except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
 try:
  a=post(env);b=post(env)
  stored=base/"pending"/(job["job_id"]+".json")
  noncefile=base/"used-nonces"/(env["nonce"]+".json")
  ok=a[0]==202 and b[0]==403 or a[0]==202 and b[0]==409
  ok=ok and stored.exists() and noncefile.exists() and not list((base/"pending").glob("*.partial"))
  print(json.dumps({"schema":"SignedHttpQueueCanary.v1","status":"PASS" if ok else "FAIL","first":a,"replay":b,"atomic_job":stored.exists(),"nonce_persisted":noncefile.exists()},indent=2))
 finally:server.shutdown();server.server_close()
 raise SystemExit(0 if ok else 1)
