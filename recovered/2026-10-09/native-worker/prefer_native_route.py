from pathlib import Path
p=Path(r"F:\Remaster Framework\orchestrator\control-plane\orch_k003.py")
s=p.read_text()
old='return sorted(c,key=lambda x:x["worker_id"])[0] if c else None'
new='return sorted(c,key=lambda x:(x.get("adapter")!="NativeLocalQueue",x["worker_id"]))[0] if c else None'
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding="utf-8")
print("ROUTING_NATIVE_PREFERRED")
