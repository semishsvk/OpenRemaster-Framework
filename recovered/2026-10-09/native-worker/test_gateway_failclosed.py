import json,threading,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
import gateway
gateway.KEYFILE=Path(__file__).parent/"secrets"/"intentionally-absent-test.key"
server=ThreadingHTTPServer(("127.0.0.1",0),gateway.Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 url="http://127.0.0.1:"+str(server.server_port)+"/v1/jobs"
 request=urllib.request.Request(url,data=b'{"schema":"NativeJobEnvelope.v1"}',headers={"Content-Type":"application/json"},method="POST")
 try:
  urllib.request.urlopen(request,timeout=3)
  code=200;body={}
 except urllib.error.HTTPError as e:
  code=e.code;body=json.loads(e.read())
 ok=code==503 and body.get("reason")=="KEY_NOT_PROVISIONED"
 print(json.dumps({"schema":"GatewayFailClosedCanary.v1","status":"PASS" if ok else "FAIL","http_status":code,"response":body},indent=2))
finally:server.shutdown();server.server_close()
raise SystemExit(0 if ok else 1)
