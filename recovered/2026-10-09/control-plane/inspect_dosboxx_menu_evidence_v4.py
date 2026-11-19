from pathlib import Path
import json
r=Path(__file__).resolve().parents[2]/"runtime-test"/"results"
p=r/"openzork-dosboxx-autotype-dbb45ef149"/"result.json"
d=json.loads(p.read_text())
print(json.dumps({"status":d.get("diagnostic_capture_status"),
"menu":d.get("dosboxx_owned_window_menu"),"reason":d.get("failure_reason"),
"end_exit":d.get("exit_code")},ensure_ascii=False))
