from pathlib import Path
import json
r=Path(__file__).resolve().parents[2]/"runtime-test"/"results"
items=sorted(r.glob("fidelity-passive-gui-fixture-*"),key=lambda p:p.stat().st_mtime,reverse=True)[:5]
out=[]
for p in items:
 f=p/"result.json"
 if f.is_file():
  a=json.loads(f.read_text())
  out.append({"run":p.name,"reason":a.get("failure_reason"),"exit":a.get("exit_code"),
    "diag_status":a.get("diagnostic_capture_status"),"capture_integrity":a.get("capture_integrity"),
    "WM_CLOSE":a.get("wm_close_sent_to_owned_window"),"graceful_timeout":a.get("graceful_close_timeout"),
    "hwnd":(a.get("runtime_window") or {}).get("hwnd"),"capture_present":bool(a.get("capture_evidence"))})
print(json.dumps(out,ensure_ascii=False))
