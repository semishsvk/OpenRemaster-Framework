import hashlib,json,shutil,tempfile
from pathlib import Path

def tree_fp(root):
 rows=[]
 for p in sorted(x for x in Path(root).rglob("*") if x.is_file()):
  rel=p.relative_to(root).as_posix()
  rows.append((rel,hashlib.sha256(p.read_bytes()).hexdigest()))
 return hashlib.sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest(),rows

with tempfile.TemporaryDirectory() as td:
 td=Path(td); src=td/"source"; src.mkdir()
 (src/"a.txt").write_text("alpha",encoding="utf-8"); (src/"sub").mkdir(); (src/"sub"/"b.bin").write_bytes(b"beta")
 manifest=[{"path":p.relative_to(src).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(x for x in src.rglob("*") if x.is_file())]
 a=td/"A"; b=td/"B"; a.mkdir(); b.mkdir()
 for e in manifest:
  for dst in (a,b):
   q=dst/e["path"]; q.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src/e["path"],q)
 fpa,ra=tree_fp(a); fpb,rb=tree_fp(b)
 assert fpa==fpb and ra==rb
 print(json.dumps({"schema":"DoubleRehydrationCanary.v1","status":"PASS","semantic_fingerprint":fpa,"files":len(ra)}))
