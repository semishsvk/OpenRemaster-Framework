"""Read-only TGA header survey to find original panorama scene families matching a saved state.
Does not decode compressed bulk data or modify authoritative corpus.
"""
from pathlib import Path
from collections import Counter,defaultdict
import struct,json
R=Path(__file__).resolve().parents[2]
source=R/"source"/"Zork Nemesis"
rows=[]
count=0
for data in ("DATA1","DATA2","DATA3"):
 folder=source/data/"ZASSETS"
 if not folder.is_dir():continue
 for p in folder.rglob("*.TGA"):
  count+=1
  try:
   with open(p,"rb") as f:h=f.read(18)
   if len(h)!=18:continue
   width,height=struct.unpack_from("<HH",h,12)
   typ=h[2];bpp=h[16]
   if (width,height) in ((320,1440),(1440,320),(320,720),(640,2880),(720,320),(320,960)):
    rows.append({"file":str(p.relative_to(source)),"name":p.name,"location":data,
      "dimensions":[width,height],"type":typ,"bpp":bpp,"bytes":p.stat().st_size})
  except OSError:pass
c=Counter(tuple(x["dimensions"]) for x in rows)
pref=Counter(x["name"][:2] for x in rows)
out=R/"runtime-test"/"results"/"openzork-native-panorama-header-inventory-v6.json"
data={"schema":"OpenZork.NativePanoramaHeaderInventory.v1",
      "status":"READ_ONLY_SOURCE",
      "TGA_files_read":count,"panorama_candidates":len(rows),
      "dimension_distribution":{str(k):v for k,v in c.items()},
      "name_prefixes":dict(pref),"rows":rows}
out.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"READ_ONLY","TGA_files":count,"panorama_candidates":len(rows),
"dimensions":data["dimension_distribution"],"prefixes":dict(pref),
"selected_vb":[r for r in rows if r["name"].startswith(("VB","TA","TB","TC"))][:28],
"report":str(out)},ensure_ascii=False))
