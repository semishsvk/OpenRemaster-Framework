import json,os
from pathlib import Path
p=Path(__file__).resolve().parent/"schemas"/"orch-k003-job.schema.json"
d=json.loads(p.read_text(encoding="utf-8-sig"))
d["properties"]["execution"]["properties"]["allow_owned_menu_quit"]={"type":"boolean"}
tmp=p.with_suffix(".json.v4-tmp")
tmp.write_text(json.dumps(d,indent=2),encoding="utf-8")
os.replace(tmp,p)
print(json.dumps({"schema":"OpenRemaster.OwnedMenuQuitSchema.v1","status":"PASS","attribute":"allow_owned_menu_quit"}))
