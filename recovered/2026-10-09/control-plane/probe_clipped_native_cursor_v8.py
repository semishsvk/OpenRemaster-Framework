"""Original recovered cursor template with optional clipping at WGC left boundary.
Only reads real run images and source extracted cursor. Hypothesis generation only,
not an allowed basis for input without independent positive/negative validation.
"""
from pathlib import Path
import numpy as np,json,hashlib
from PIL import Image
R=Path(__file__).resolve().parents[2]
r=R/"runtime-test"/"results"
sprite=R/"work"/"OpenZork"/"runtime"/"assets"/"cursors"/"00idlea.png"
samples=[
("r6_good",r/"openzork-native-dosboxx-extended-newgame-20261009-r6"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp"),
("r7_left",r/"openzork-native-dosboxx-newgame-skipintro-20261009-r7"/"fidelity-isolated"/"capture"/"samples"/"point-02"/"frame-0001.bmp"),
("r8_precapture_left",r/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"/"fidelity-isolated"/"input-observations"/"pre-click"/"frame-0001.bmp"),
]
with Image.open(sprite) as im: template=np.asarray(im.convert("RGBA"),dtype=np.int16)
opaque=template[:,:,3]>=190
src=template[:,:,:3]
th,tw=opaque.shape
results=[]
for name,path in samples:
 with Image.open(path) as im:
  frame=np.asarray(im.convert("RGB"),dtype=np.int16)
 png=path.with_suffix(".png")
 with Image.open(path) as im:im.convert("RGB").save(png)
 candidates=[]
 for x in range(-28,20):
  for y in range(150,501):
   x0=max(0,-x);x1=min(tw,frame.shape[1]-x)
   y0=max(0,-y);y1=min(th,frame.shape[0]-y)
   if x1<=x0 or y1<=y0:continue
   mask=opaque[y0:y1,x0:x1]
   count=int(mask.sum())
   if count<100:continue
   f=frame[y+y0:y+y1,x+x0:x+x1][mask]
   s=src[y0:y1,x0:x1][mask]
   err=np.abs(f.astype(np.float64)-s.astype(np.float64))
   rms=float(np.sqrt(np.mean(err*err)))
   candidates.append((rms,x,y,count))
 candidates.sort()
 winners=[]
 for rmse,x,y,count in candidates[:150]:
  if any(abs(x-z["x"])<7 and abs(y-z["y"])<10 for z in winners):continue
  winners.append({"x":x,"y":y,"rmse":round(rmse,3),"opaque_pixels":count})
  if len(winners)==5:break
 # Native title edges are otherwise almost black; counts highlight visible cursor.
 roi=frame[160:505,0:30].astype(np.int16)
 bright=((roi[:,:,0]>130)&(roi[:,:,1]>120)&(roi[:,:,2]>60))
 results.append({"run":name,"source_frame_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
 "left_edge_gold_bright_pixels":int(bright.sum()),
 "clipped_cursor_candidates":winners,"png":str(png)})
report={"schema":"OpenZork.NativeCursorClippedLeftEdgeProbe.v1",
"status":"READ_ONLY_EXPLORATORY_LEFT_EDGE_CURSOR_DETECTOR",
"source_cursor_sha256":hashlib.sha256(sprite.read_bytes()).hexdigest(),
"scan_area":{"x":[-28,19],"y":[150,500]},
"results":results,
"independent_fidelity_pass":False,
"guest_mouse_input_sent":False}
out=r/"openzork-native-dosboxx-cursor-guarded-newgame-20261009-r8"/"left-edge-cursor-probe-v8.json"
if out.exists():raise RuntimeError("LEFT_EDGE_PROBE_RESULT_EXISTS")
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"results":[{"run":x["run"],
"bright":x["left_edge_gold_bright_pixels"],"best":x["clipped_cursor_candidates"][:2]} for x in results],
"evidence":str(out)},ensure_ascii=False))
