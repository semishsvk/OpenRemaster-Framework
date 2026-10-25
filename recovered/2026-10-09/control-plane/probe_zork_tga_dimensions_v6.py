"""Inspect exact native TGA dimensions, row orientations and PIL support."""
import json,struct
from pathlib import Path
from collections import Counter
from PIL import Image
r=Path(__file__).resolve().parents[2]/"source"/"Zork Nemesis"
wanted=("TA30S11C.TGA","VB20S11C.TGA","VB30S11C.TGA","TB10S11C.TGA","T000B11C.TGA")
rows=[]
for d in ("DATA1","DATA2","DATA3"):
 folder=r/d
 if not folder.is_dir():continue
 for name in wanted:
  for path in folder.rglob(name):
   h=path.read_bytes()[:18]
   width,height=struct.unpack_from("<HH",h,12)
   try:
    with Image.open(path) as im:
     pil=list(im.size);format=im.format
   except Exception as ex:
    pil=None;format="ERROR_"+type(ex).__name__
   rows.append({"file":str(path.relative_to(r)),"bytes":path.stat().st_size,
    "width":width,"height":height,"type":h[2],"bpp":h[16],"pil":pil,"format":format,
    "first_bytes":h.hex()})
print(json.dumps(rows,ensure_ascii=False))
