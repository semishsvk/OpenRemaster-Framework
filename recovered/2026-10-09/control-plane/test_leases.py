import json,tempfile,time
from pathlib import Path
from leases import acquire,inspect,release
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"lease.json"
 a=acquire(p,"j","w","a1",ttl_seconds=0)
 assert a["status"]=="ACQUIRED"
 assert inspect(p)["status"]=="EXPIRED"
 b=acquire(p,"j","w","a2",ttl_seconds=60)
 assert b["status"]=="ACQUIRED" and b["lease"]["attempt_id"]=="a2"
 assert release(p,"a1") is False
 assert release(p,"a2") is True
 print(json.dumps({"schema":"StaleLeaseCanary.v1","status":"PASS"}))
