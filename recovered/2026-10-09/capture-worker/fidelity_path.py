import hashlib,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"control-plane"))
from fidelity_runtime_isolation_v1 import process_identity
def workspace_root():return Path(__file__).resolve().parents[2]
def load_process_identity(pid):return process_identity(pid)
def sha256(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def outfile(p):return Path(p)
