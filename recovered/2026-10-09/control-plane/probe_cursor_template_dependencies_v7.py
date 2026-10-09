from pathlib import Path
from PIL import Image
import importlib.util,json
R=Path(__file__).resolve().parents[2]
p=R/"work"/"OpenZork"/"runtime"/"assets"/"cursors"/"00idlea.png"
with Image.open(p) as im:
 im.load();box=im.getbbox();info={"image_size":im.size,"mode":im.mode,"alpha_bbox":box}
print(json.dumps({"packages":{x:bool(importlib.util.find_spec(x)) for x in ("cv2","scipy","numpy","PIL")},
"cursor":info}))
