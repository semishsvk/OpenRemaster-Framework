from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]/"runtime-test"/"results"
d=sorted(root.glob("openzork-newgame-owned-mouse-*"),key=lambda p:p.stat().st_mtime,reverse=True)
rows=[]
for folder in d[:3]:
 r=json.loads((folder/"result.json").read_text()) if (folder/"result.json").is_file() else {}
 v=json.loads((folder/"validation-result.json").read_text()) if (folder/"validation-result.json").is_file() else {}
 f=folder/"fidelity-isolated"/"capture"/"frame-0001.bmp"
 rows.append({"run":folder.name,"status":r.get("status"),"reason":r.get("failure_reason"),
 "diagnostic_status":r.get("diagnostic_capture_status"),"runtime_exit":r.get("exit_code"),
 "window":r.get("runtime_window"),"owned_events":r.get("owned_input_posted_events"),
 "frame_exists":f.is_file(),"frame_path":str(f),"validator":v.get("status")})
print(json.dumps(rows))
