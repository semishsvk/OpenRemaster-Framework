import importlib.util,json
from PIL import Image
from pathlib import Path
r=Path(__file__).resolve().parents[2]
folder=r/"work"/"OpenZork"/"runtime"/"assets"/"cursors"
c=[]
for p in sorted(folder.glob("*.png")):
 with Image.open(p) as i:
  im=i.convert("RGBA")
  c.append({"name":p.name,"size":list(i.size),"bbox":im.getchannel("A").getbbox()})
print(json.dumps({"packages":{m:bool(importlib.util.find_spec(m)) for m in ("cv2","numpy","PIL","scipy")},"cursors":c}))
