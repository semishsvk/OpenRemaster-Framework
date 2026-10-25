import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
queue=root/"queue"
checks={}
checks["python"]=sys.executable
checks["username"]=os.environ.get("USERNAME")
checks["source_read"]=(Path(r"F:\Remaster Framework\source").is_dir())
checks["control_read"]=(root.parent/"control-plane"/"orch_k003.py").is_file()
checks["queue_read"]=(queue/"pending").is_dir()
checks["source_write_test"]="NOT_ATTEMPTED_NON_DESTRUCTIVE"
checks["queue_write_test"]="NOT_ATTEMPTED_NON_DESTRUCTIVE"
print(json.dumps({"schema":"NativeWorkerIdentityProbe.v1","checks":checks},indent=2))
