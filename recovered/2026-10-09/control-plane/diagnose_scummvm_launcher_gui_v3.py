"""Capture the exact ScummVM fallback Launcher window via owned HWND, diagnostic only."""
from datetime import datetime,timezone
from pathlib import Path
import json,sys,subprocess,uuid
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/"openzork-supervised-oracle-passive-80efcbbbd.json"
assert source.is_file()
job=json.loads(source.read_text())
job["job_id"]="openzork-scummvm-launcher-diagnostic-"+uuid.uuid4().hex[:8]
job["task"]="ScummVMLauncherFallbackDiagnostic"
job["execution"]["window_title_contains"]="ScummVM 2.0.0"
job["execution"]["require_audio"]=False
job["required_capabilities"]=[c for c in job["required_capabilities"] if c!="audio.process_loopback"]
out=ROOT/"runtime-test"/"results"/job["job_id"]
inp=ROOT/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(job["job_id"]+".json")
inp.write_text(json.dumps(job,indent=2))
r=subprocess.run([sys.executable,"-B",str(Path(__file__).parent/"orch_k003.py"),str(inp)],
                 capture_output=True,text=True,timeout=40)
result=json.loads((out/"result.json").read_text())
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
png=out/"scummvm-launcher.png"
if frame.is_file():
 with Image.open(frame) as im: im.save(png)
report={"schema":"OpenZork.ScummVMLauncherBindingDiagnostic.v1",
"status":"CAPTURED_DIAGNOSTIC" if frame.is_file() else "NO_DIAGNOSTIC_FRAME",
"reason":result.get("failure_reason"),"worker_exit":r.returncode,
"window":result.get("runtime_window"),"window_history":result.get("owned_window_history"),
"capture_path":str(png) if png.is_file() else None,
"owned_pid":(result.get("runtime_identity") or {}).get("pid"),"stdout_tail":r.stdout[-350:],
"timestamp":datetime.now(timezone.utc).isoformat(),"fidelity":"NOT_VERIFIED"}
(out/"launcher-diagnostic.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(0 if png.is_file() else 1)
