"""Read-only contact sheet of raw recovered OpenZork panorama data."""
from pathlib import Path
from PIL import Image, ImageDraw
import json
R=Path(__file__).resolve().parents[2]
src=R/"work"/"OpenZork"/"runtime"/"assets"
dest=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"
names=["VB20S11C.ppm","VB30S11C.ppm"]
out=Image.new("RGB",(1100,800),(25,25,25))
draw=ImageDraw.Draw(out)
records=[]
for i,name in enumerate(names):
 p=src/name
 with Image.open(p) as im:
  img=im.convert("RGB")
  size=img.size
  thumb=img.copy()
  thumb.thumbnail((1060,215),Image.Resampling.BILINEAR)
  out.paste(thumb,(20,30+i*260))
 records.append({"scene":name,"file":str(p),"dimension":list(size)})
 draw.text((20,8+i*260),name+" recovered raw panorama",fill=(242,242,242))
gold=dest/"fidelity-isolated"/"capture"/"golden-scene-viewport-768x480.png"
with Image.open(gold) as im:
 preview=im.convert("RGB")
 preview.thumbnail((500,230),Image.Resampling.BILINEAR)
 out.paste(preview,(20,550))
draw.text((20,527),"Stable Golden Scene ScummVM save slot 0",fill=(242,242,242))
result=dest/"golden-vb20-vb30-raw-panorama-reference.png"
out.save(result)
print(json.dumps({"status":"RAW_PIXELS_ONLY","candidates":records,"sheet":str(result)}))
