import json,hmac,hashlib,time,threading,urllib.request,urllib.error,tempfile,secrets,subprocess,sys
from pathlib import Path
from http.server import ThreadingHTTPServer
import gateway,transport_contract
root=Path(__file__).resolve().parent
real_queue=root/"queue"
with tempfile.TemporaryDirectory(prefix="native-http-e2e-") as tmp:
 base=Path(tmp)
 for name in ("pending","running","done","failed"): (base/name).mkdir()
 key=secrets.token_bytes(32);keyfile=base/"test.key";keyfile.write_bytes(key)
 gateway.QUEUE=base;gateway.KEYFILE=keyfile;transport_contract.QUEUE=base
 job=json.loads(Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json").read_text())
 job["job_id"]="signed-http-godot-e2e-20261008"
 env={"schema":"NativeJobEnvelope.v1","audience":"HomePC-NativeWorker","timestamp":int(time.time()),"nonce":secrets.token_hex(16),"job":job}
 env["mac"]=hmac.new(key,json.dumps(env,sort_keys=True,separators=(",",":")).encode(),hashlib.sha256).hexdigest()
 server=ThreadingHTTPServer(("127.0.0.1",0),gateway.Handler)
 t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
 try:
  req=urllib.request.Request("http://127.0.0.1:"+str(server.server_port)+"/v1/jobs",data=json.dumps(env).encode(),method="POST")
  with urllib.request.urlopen(req,timeout=5) as response:accepted=response.status==202
  pending=base/"pending"/(job["job_id"]+".json")
  if not accepted or not pending.exists():raise RuntimeError("HTTP_NOT_ACCEPTED")
  target=real_queue/"pending"/pending.name
  if target.exists():raise RuntimeError("JOB_ALREADY_EXISTS")
  target.write_bytes(pending.read_bytes())
  deadline=time.monotonic()+30
  receipt=real_queue/"done"/(job["job_id"]+".receipt.json")
  while time.monotonic()<deadline and not receipt.exists():time.sleep(0.5)
  data=json.loads(receipt.read_text()) if receipt.exists() else {}
  ok=data.get("returncode")==0
  print(json.dumps({"schema":"SignedHttpGodotE2E.v1","status":"PASS" if ok else "FAIL","http_accepted":accepted,"worker_receipt":receipt.exists(),"orchestrator_exit":data.get("returncode")},indent=2))
 finally:server.shutdown();server.server_close()
 raise SystemExit(0 if ok else 1)
