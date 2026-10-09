"""Durable, fail-closed proposal adapter. Never executes jobs or grants leases."""
import json,hashlib,os
from pathlib import Path
from dynamic_scheduler_core_v1 import Task,Worker,plan

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':')).encode()

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def proposal(pool_path, capacity_path, output_path):
    pool_path,capacity_path,output_path=map(Path,(pool_path,capacity_path,output_path))
    if output_path.exists():
        raise FileExistsError("immutable proposal already exists")
    pool_bytes=pool_path.read_bytes();cap_bytes=capacity_path.read_bytes()
    pool=json.loads(pool_bytes);cap=json.loads(cap_bytes)
    if pool.get("schema")!="OpenRemaster.TaskPool.v1" or cap.get("schema")!="OpenRemaster.CapacitySnapshot.v1":
        raise ValueError("schema mismatch")
    if not cap.get("complete") or not cap.get("fresh") or not cap.get("source_authorized"):
        raise ValueError("capacity snapshot is not authoritative")
    if not isinstance(pool.get("tasks"),list) or not isinstance(cap.get("workers"),list):
        raise ValueError("incomplete inputs")
    tasks=[Task(**t) for t in pool["tasks"]]
    workers=[Worker(**w) for w in cap["workers"]]
    result=plan(tasks,workers,cap.get("running"),max_workers=3,max_heavy=3)
    record={"schema":"OpenRemaster.DispatchProposal.v1","status":result["status"],
            "source_sha256":{"pool":hashlib.sha256(pool_bytes).hexdigest(),
                             "capacity":hashlib.sha256(cap_bytes).hexdigest()},
            "result":result,"dispatch_executed":False,"lease_modified":False,
            "approval":"NOT_GRANTED_BY_PROPOSAL"}
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with output_path.open("xb") as f:
        f.write(canonical(record));f.flush();os.fsync(f.fileno())
    return record
