import json,tempfile,time
from pathlib import Path
from leases import acquire,renew,inspect,release
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"lease.json"
 assert acquire(p,"j","w","a1",1)["status"]=="ACQUIRED"
 time.sleep(.6)
 x=renew(p,"a1",2); assert x["status"]=="RENEWED"
 time.sleep(.7)
 assert inspect(p)["status"]=="ACTIVE"
 assert renew(p,"wrong",2)["status"]=="REJECTED"
 assert release(p,"a1")
 print(json.dumps({"schema":"LeaseHeartbeatCanary.v1","status":"PASS"}))
