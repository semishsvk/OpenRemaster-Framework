import json, subprocess, sys, tempfile
from pathlib import Path
v=Path(__file__).with_name("validate_interaction_audio.py")
good={"entries":[
 {"interaction_id":"x/open","game":"x","room_or_context":"r","trigger_or_object":"door","branch":"success","classification":"SOURCE_AUDIO_VERIFIED","source_evidence":["corpus"],"asset_if_any":"door.wav","asset_sha256_if_any":"a"*64,"runtime_event":"DOOR_OPEN","test_status":"PASS"},
 {"interaction_id":"x/locked","game":"x","room_or_context":"r","trigger_or_object":"door","branch":"locked","classification":"NO_AUDIO_BY_SOURCE","source_evidence":["corpus"],"runtime_event":None,"test_status":"PASS","observed_audio_events":[]},
 {"interaction_id":"x/unknown","game":"x","room_or_context":"r","trigger_or_object":"thing","branch":"use","classification":"HOLD_UNRESOLVED","source_evidence":["insufficient"],"runtime_event":None,"test_status":"BLOCKED"}
]}
bad={"entries":[dict(good["entries"][1], observed_audio_events=["generic.wav"])]}
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"good.json";p.write_text(json.dumps(good)); a=subprocess.run([sys.executable,str(v),str(p)],capture_output=True,text=True)
 q=Path(td)/"bad.json";q.write_text(json.dumps(bad)); b=subprocess.run([sys.executable,str(v),str(q)],capture_output=True,text=True)
 ok=a.returncode==0 and b.returncode!=0 and "FORBIDDEN_AUDIO_EMITTED" in b.stdout
 print(json.dumps({"status":"PASS" if ok else "FAIL","positive_rc":a.returncode,"negative_rc":b.returncode}))
 raise SystemExit(0 if ok else 1)
