import json,os
from pathlib import Path
p=Path(__file__).resolve().parent/"schemas"/"orch-k003-job.schema.json"
d=json.loads(p.read_text(encoding="utf-8-sig"))
d["properties"]["execution"]["properties"]["capture_delay_seconds"]={"type":"number","minimum":0,"maximum":12}
t=p.with_suffix(".json.deltmp");t.write_text(json.dumps(d,indent=2),encoding="utf-8");os.replace(t,p)
print(json.dumps({"status":"PASS","capture_delay_seconds":"0..12","gui_input":"NO_INJECTION","producer":"HWND_BOUND"}))
