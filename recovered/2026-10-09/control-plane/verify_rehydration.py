import argparse, datetime, hashlib, json, platform, sys
from pathlib import Path
def h(p):
 x=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1048576),b""): x.update(b)
 return x.hexdigest()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("manifest"); ap.add_argument("out"); a=ap.parse_args()
 root=Path(a.project); mpath=Path(a.manifest); m=json.loads(mpath.read_text(encoding="utf-8-sig")); failures=[]; checked=[]
 for e in m.get("provenance",[]):
  p=root/e["path"]
  if not p.is_file(): failures.append({"path":e["path"],"reason":"MISSING"}); continue
  actual=h(p); checked.append({"path":e["path"],"sha256":actual})
  if actual!=e["sha256"]: failures.append({"path":e["path"],"reason":"HASH_MISMATCH","expected":e["sha256"],"actual":actual})
 out={"schema":"RehydrationVerification.v1","captured_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"project_root":str(root),"manifest":str(mpath),"manifest_sha256":h(mpath),"checked_files":len(checked),"declared_files":len(m.get("provenance",[])),"status":"PASS" if not failures else "FAIL","failures":failures,"runtime_fingerprint":{"machine":platform.node(),"os":platform.platform(),"python":platform.python_version()}}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2),encoding="utf-8"); print(json.dumps(out,indent=2)); return 0 if not failures else 1
if __name__=="__main__": sys.exit(main())
