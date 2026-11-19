import getpass,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
q=root/"queue"
source=Path(r"F:\Remaster Framework\source")
out=q/"done"/"dedicated-identity-evidence.json"
checks={"identity":getpass.getuser(),"env_username":os.environ.get("USERNAME"),"python":sys.executable,"source_read":source.is_dir(),"control_read":(root.parent/"control-plane"/"orch_k003.py").is_file(),"queue_read":(q/"pending").is_dir()}
try:
 p=q/"done"/"dedicated-write-probe.tmp"
 p.write_text("test",encoding="utf-8");p.unlink();checks["queue_write"]="PASS"
except Exception as e:checks["queue_write"]="FAIL:"+type(e).__name__
try:
 p=source/"__openremaster_should_be_denied__.tmp"
 with p.open("x") as f:f.write("test")
 p.unlink();checks["source_write_denied"]=False
except PermissionError:checks["source_write_denied"]=True
except Exception as e:checks["source_write_denied"]="UNKNOWN:"+type(e).__name__
status="PASS" if checks["identity"].lower()=="openremasterworker" and checks["queue_write"]=="PASS" and checks["source_write_denied"] is True and checks["control_read"] else "FAIL"
out.write_text(json.dumps({"schema":"DedicatedIdentityEvidence.v1","status":status,"checks":checks},indent=2),encoding="utf-8")
sys.exit(0 if status=="PASS" else 1)
