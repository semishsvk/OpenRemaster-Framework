"""Bounded settled-state probe after native DOSBox-X AUTOTYPE. 28s default.
Runs original ZORKDOS binary in private sandbox, no global host input, no fidelity claim.
"""
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image,ImageStat
import json,uuid,subprocess,sys
from fidelity_runtime_isolation_v1 import gui_conflicts,sha256
root=Path(__file__).resolve().parents[2]
cp=Path(__file__).parent
reference="openzork-dosboxx-autotype-3956dd7a57"
source=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(reference+".json")
assert source.is_file()
base=json.loads(source.read_text(encoding="utf-8"))
run="openzork-dosboxx-late-autotype-"+uuid.uuid4().hex[:10]
base["job_id"]=run;base["task"]="NativeZORKDOSPostAutotypeLateFrameDiagnostic"
base["execution"]["capture_delay_seconds"]=28.0
base["execution"]["timeout_seconds"]=42
inp=root/"runtime-test"/"jobs"/"_fidelity-isolation-tests"/(run+".json")
inp.write_text(json.dumps(base,indent=2))
before={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
p=subprocess.run([sys.executable,"-B",str(cp/"orch_k003.py"),str(inp)],capture_output=True,text=True,timeout=75)
out=root/"runtime-test"/"results"/run
result=json.loads((out/"result.json").read_text()) if (out/"result.json").is_file() else {}
receipt=json.loads((out/"control-receipt.json").read_text()) if (out/"control-receipt.json").is_file() else {}
frame=out/"fidelity-isolated"/"capture"/"frame-0001.bmp"
stats={}
if frame.is_file():
 with Image.open(frame) as i:
  rgb=i.convert("RGB");rgb.save(frame.with_suffix(".png"))
  d=ImageStat.Stat(rgb)
  stats={"shape":[rgb.width,rgb.height],"mean":[round(x,1) for x in d.mean],
         "stdev":[round(x,1) for x in d.stddev]}
after={w["pid"]:w["creation_ticks_100ns"] for w in gui_conflicts()}
safe=(p.returncode==2 and receipt.get("status")=="BLOCKED"
      and result.get("capture_integrity")=="PASS"
      and result.get("diagnostic_capture_status")=="PASS"
      and result.get("exit_code")==0 and frame.is_file()
      and all(after.get(pid)==ticks for pid,ticks in before.items()))
report={"schema":"OpenZork.DOSBoxXLateCaptureDiagnostic.v1",
        "status":"TECHNICAL_CAPTURE_PASS_STATE_UNALIGNED" if safe else "BLOCKED",
        "timestamp":datetime.now(timezone.utc).isoformat(),"run_id":run,
        "emulator_sha256":(result.get("runtime_identity") or {}).get("executable_sha256"),
        "native_game_executed":"ZORKDOS_EXE_READ_ONLY","auto_type":"INTERNAL_ENTER",
        "capture_delay_seconds":28,
        "frame":str(frame.with_suffix(".png")) if frame.is_file() else None,
        "frame_sha256":sha256(frame) if frame.is_file() else None,
        "frame_stats":stats,
        "process_exit":result.get("exit_code"),
        "reason":result.get("failure_reason"),
        "menu_quit":result.get("owned_dosboxx_menu_quit"),
        "preexisting_gui_pids_preserved":sum(after.get(pid)==t for pid,t in before.items()),
        "preexisting_gui_pids":len(before),"fidelity_verified":False}
target=out/"late-capture-report.json";out.mkdir(parents=True,exist_ok=True)
target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps(dict(report,evidence=str(target)),ensure_ascii=False))
raise SystemExit(0 if safe else 1)
