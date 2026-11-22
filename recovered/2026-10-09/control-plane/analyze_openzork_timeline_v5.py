"""Real local WGC frames only. Builds evidence contact sheet, not generated art.
Analysis is descriptive technical telemetry, not a fidelity comparator.
"""
from PIL import Image,ImageDraw,ImageStat
from pathlib import Path
import json,sys,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
if len(sys.argv)>1:run_id=sys.argv[1]
else:
 x=sorted((ROOT/"runtime-test"/"results").glob("openzork-dosboxx-threepoint-*"),key=lambda p:p.stat().st_mtime,reverse=True)
 if not x:raise FileNotFoundError("No timeline run")
 run_id=x[0].name
folder=ROOT/"runtime-test"/"results"/run_id
manifest=folder/"fidelity-isolated"/"capture"/"capture-attestation.json"
assert manifest.is_file(),str(manifest)
master=json.loads(manifest.read_text())
assert master.get("capture_schedule_schema")=="OpenRemaster.BoundedFrameSchedule.v1"
rows=master["frames"]
canvas=Image.new("RGB",(860,len(rows)*400),(24,24,24))
draw=ImageDraw.Draw(canvas)
data=[]
for i,row in enumerate(rows,1):
 f=manifest.parent/row["path"]
 with Image.open(f) as image:
  shot=image.convert("RGB")
  w,h=shot.size
  ratio=min(820/w,348/h)
  shot=shot.resize((round(w*ratio),round(h*ratio)),Image.Resampling.NEAREST)
  canvas.paste(shot,(20,40+(i-1)*400))
  raw=np.asarray(image.convert("RGB"),dtype=np.uint8)
  sd=[round(float(x),1) for x in raw.std(axis=(0,1))]
  mn=[round(float(x),1) for x in raw.mean(axis=(0,1))]
 draw.text((20,(i-1)*400+10),f"Point {i} / {row['requested_at_seconds']}s / native WGC / PID {master['pid']}",fill=(240,240,240))
 data.append({"index":i,"planned_offset_s":row["requested_at_seconds"],"real_offset_s":row["started_at_seconds"],
             "width":w,"height":h,"mean_rgb":mn,"stddev_rgb":sd,
             "sha256":row["sha256"],"file":str(f)})
out=folder/"original-runtime-timeline.png"
canvas.save(out,format="PNG")
result={
 "schema":"OpenZork.NativeZORKDOSTimeLineObservation.v1",
 "status":"DIAGNOSTIC_CONTACT_SHEET_REAL_CAPTURE_ONLY",
 "run_id":run_id,"owner_pid":master["pid"],"owner_hwnd":master["hwnd"],
 "original_runtime_frames":data,"contact_sheet_path":str(out),
 "contact_sheet_sha256":hashlib.sha256(out.read_bytes()).hexdigest(),
 "same_state_reconstructed_comparison":"NOT_PERFORMED",
 "gameplay_fidelity":"NOT_VERIFIED"}
dst=folder/"timeline-analysis.json"
dst.write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({"status":result["status"],"run_id":run_id,
 "images":[{"s":x["planned_offset_s"],"mean_rgb":x["mean_rgb"],"image":x["file"],"sha256":x["sha256"]} for x in data],
 "contact_sheet":str(out),"analysis":str(dst)}))
