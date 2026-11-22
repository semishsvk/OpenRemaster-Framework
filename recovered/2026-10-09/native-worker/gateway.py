import json,os,threading,re
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from transport_contract import validate_envelope
ROOT=Path(__file__).resolve().parent
QUEUE=ROOT/"queue"
KEYFILE=ROOT/"secrets"/"transport.key"
LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  if self.path!="/v1/jobs":self.send_error(404);return
  if self.client_address[0] not in ("127.0.0.1","::1"):self.send_error(403);return
  try:
   size=int(self.headers.get("Content-Length","0"))
   if not 0<size<=65536:self.send_error(413);return
   env=json.loads(self.rfile.read(size))
   key=KEYFILE.read_bytes()
   with LOCK:
    reason=validate_envelope(env,key)
    if reason!="PASS":self.respond(403,{"status":"REJECTED","reason":reason});return
    nonce=env.get("nonce")
    if not isinstance(nonce,str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,96}",nonce):
     self.respond(403,{"status":"REJECTED","reason":"INVALID_NONCE"});return
    used=QUEUE/"used-nonces"
    used.mkdir(exist_ok=True)
    marker=used/(nonce+".json")
    try:
     with marker.open("x",encoding="utf-8") as f:
      json.dump({"nonce":nonce,"job_id":env["job"]["job_id"]},f)
      f.flush();os.fsync(f.fileno())
    except FileExistsError:
     self.respond(409,{"status":"REJECTED","reason":"NONCE_REPLAY"});return
    job=env["job"];jid=job["job_id"]
    temp=QUEUE/"pending"/(jid+".partial")
    path=QUEUE/"pending"/(jid+".json")
    try:
     with temp.open("x",encoding="utf-8") as f:
      json.dump(job,f);f.flush();os.fsync(f.fileno())
     os.replace(temp,path)
    except Exception:
     temp.unlink(missing_ok=True)
     self.respond(503,{"status":"BLOCKED","reason":"ENQUEUE_FAILED_NONCE_CONSUMED"});return
   self.respond(202,{"status":"QUEUED","job_id":jid})
  except FileNotFoundError:self.respond(503,{"status":"BLOCKED","reason":"KEY_NOT_PROVISIONED"})
  except Exception:self.respond(400,{"status":"REJECTED"})
 def respond(self,code,obj):
  data=json.dumps(obj).encode()
  self.send_response(code);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
if __name__=="__main__":
 ThreadingHTTPServer(("127.0.0.1",8765),Handler).serve_forever()
