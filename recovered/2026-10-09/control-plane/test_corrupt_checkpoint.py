import hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
 root=Path(td)/"project"; root.mkdir()
 f=root/"a.bin"; f.write_bytes(b"good")
 good=hashlib.sha256(b"good").hexdigest()
 manifest=Path(td)/"manifest.json"; manifest.write_text(json.dumps({"provenance":[{"path":"a.bin","sha256":good}]}),encoding="utf-8")
 out=Path(td)/"out.json"
 p=subprocess.run([sys.executable,str(ROOT/"verify_rehydration.py"),str(root),str(manifest),str(out)],capture_output=True,text=True)
 assert p.returncode==0 and json.loads(out.read_text())["status"]=="PASS"
 f.write_bytes(b"corrupt")
 p=subprocess.run([sys.executable,str(ROOT/"verify_rehydration.py"),str(root),str(manifest),str(out)],capture_output=True,text=True)
 report=json.loads(out.read_text())
 assert p.returncode==1 and report["status"]=="FAIL" and report["failures"][0]["reason"]=="HASH_MISMATCH"
 print(json.dumps({"schema":"CorruptCheckpointCanary.v1","status":"PASS","detected":report["failures"][0]["reason"]}))
