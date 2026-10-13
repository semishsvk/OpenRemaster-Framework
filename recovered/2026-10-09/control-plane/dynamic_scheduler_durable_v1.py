"""Durable synthetic scheduler state with exclusive checkpoint creation.
This is an offline test harness, not a native dispatch service.
"""
import hashlib,json,os
from pathlib import Path
from dynamic_scheduler_simulator_v1 import simulate
def encoded(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return hashlib.sha256(encoded(x)).hexdigest()
def seal(path,document):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("xb") as f:f.write(encoded(document));f.flush();os.fsync(f.fileno())
    return hashlib.sha256(p.read_bytes()).hexdigest()
def run_synthetic(run_dir,tasks,workers,outcomes,run_id,max_ticks=100):
    root=Path(run_dir)
    if not run_id or "/" in run_id or "\\" in run_id:raise ValueError("BAD_RUN_ID")
    if root.exists() and any(root.iterdir()):raise FileExistsError("EXISTING_RUN_REQUIRES_RECONCILIATION")
    root.mkdir(parents=True,exist_ok=True)
    source={"run_id":run_id,"tasks":[vars(t) for t in tasks],
            "workers":[vars(w) for w in workers],"outcomes":outcomes}
    seal(root/"inputs.json",source)
    result=simulate(tasks,workers,outcomes,max_ticks=max_ticks)
    previous="0"*64
    for i,event in enumerate(result["events"]):
        entry={"schema":"OpenRemaster.SyntheticEvent.v1","sequence":i,
               "previous_sha256":previous,"event":event}
        previous=seal(root/f"event-{i:06d}.json",entry)
    receipt={"schema":"OpenRemaster.SyntheticRunReceipt.v1","run_id":run_id,
             "status":result["status"],"input_sha256":digest(source),
             "events":len(result["events"]),"last_event_sha256":previous,
             "pending":result["pending"],"native_execution":False}
    seal(root/"receipt.json",receipt)
    return receipt
def verify_synthetic(run_dir):
    root=Path(run_dir);receipt=json.loads((root/"receipt.json").read_bytes())
    inp=json.loads((root/"inputs.json").read_bytes())
    if digest(inp)!=receipt["input_sha256"]:return False
    previous="0"*64
    events=sorted(root.glob("event-*.json"))
    if len(events)!=receipt["events"]:return False
    for i,p in enumerate(events):
        e=json.loads(p.read_bytes())
        if e["sequence"]!=i or e["previous_sha256"]!=previous:return False
        previous=hashlib.sha256(p.read_bytes()).hexdigest()
    return previous==receipt["last_event_sha256"] and receipt["native_execution"] is False
