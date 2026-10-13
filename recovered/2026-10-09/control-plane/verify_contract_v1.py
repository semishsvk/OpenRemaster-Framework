import json,hashlib,sys
from pathlib import Path
m=Path(sys.argv[1]); root=Path(sys.argv[2]); d=json.loads(m.read_text(encoding="utf-8")); bad=[]; tree=hashlib.sha256()
for x in d["inputs"]:
 p=root/x["path"]
 if not p.is_file(): bad.append({"path":x["path"],"reason":"MISSING"}); continue
 b=p.read_bytes(); s=hashlib.sha256(b).hexdigest()
 if s!=x["sha256"] or len(b)!=x["size"]: bad.append({"path":x["path"],"reason":"MISMATCH"})
 tree.update(f'{x["path"]}|{len(b)}|{s}\n'.encode())
actual=tree.hexdigest()
out={"schema":"RehydrationContractVerification.v1","manifest":str(m),"checked":len(d["inputs"]),"expected_tree_sha256":d["tree_sha256"],"actual_tree_sha256":actual,"status":"PASS" if not bad and actual==d["tree_sha256"] else "FAIL","failures":bad}
print(json.dumps(out,indent=2));sys.exit(0 if out["status"]=="PASS" else 1)
