import json,hmac,hashlib,time,threading,urllib.request,urllib.error,tempfile,secrets,concurrent.futures
from pathlib import Path
from http.server import ThreadingHTTPServer
import gateway,transport_contract
with tempfile.TemporaryDirectory(prefix="native-concurrent-") as tmp:
 base=Path(tmp)
 for n in ("pending","running","done","failed"): (base/n).mkdir()
 key=secrets.token_bytes(32);keyfile=base/"key";keyfile.write_bytes(key)
 gateway.QUEUE=base;gateway.KEYFILE=keyfile;transport_contract.QUEUE=base
 job=json.loads(Path(r"F:\Remaster Framework\runtime-test\jobs\ORCH-K003-OpenAzrael-KG001.json").read_text())
 job["job_id"]="concurrent-replay-test-20261008"
 env={"schema":"NativeJobEnvelope.v1","audience":"HomePC-NativeWorker","timestamp":int(time.time()),"nonce":secrets.token_hex(16),"job":job}
 env["mac"]=hmac.new(key,json.dumps(env,sort_keys=True,separators=(",",":")).encode(),hashlib.sha256).hexdigest()
 server=ThreadingHTTPServer(("127.0.0.1",0),gateway.Handler)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 def post():
  req=urllib.request.Request("http://127.0.0.1:"+str(server.server_port)+"/v1/jobs",data=json.dumps(env).encode(),method="POST")
  try:
   with urllib.request.urlopen(req,timeout=6) as r:return r.status
  except urllib.error.HTTPError as e:return e.code
 try:
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:post(),range(16)))
  ok=results.count(202)==1 and len(list((base/"pending").glob("*.json")))==1 and len(list((base/"used-nonces").glob("*.json")))==1
  print(json.dumps({"schema":"ConcurrentReplayCanary.v1","status":"PASS" if ok else "FAIL","accepted":results.count(202),"rejected":len(results)-results.count(202),"codes":results},indent=2))
 finally:server.shutdown();server.server_close()
 raise SystemExit(0 if ok else 1)
