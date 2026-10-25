import http.server,pathlib
ROOT=pathlib.Path(r'F:\Remaster Framework\orchestrator\artifact-bridge')
class H(http.server.SimpleHTTPRequestHandler):
 def __init__(self,*a,**k): super().__init__(*a,directory=str(ROOT),**k)
 def end_headers(self): self.send_header('Cache-Control','no-store'); super().end_headers()
http.server.ThreadingHTTPServer(('127.0.0.1',8787),H).serve_forever()
