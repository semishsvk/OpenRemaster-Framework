"""Native ZVision TGZ, not standard TGA. Read-only header family inventory."""
from pathlib import Path
from collections import Counter
import struct,json
r=Path(__file__).resolve().parents[2]
src=r/"source"/"Zork Nemesis"/"DATA2"/"ZASSETS"/"CONSERV"
files=list(src.glob("*.TGA"))
pan=[]
for file in files:
 with open(file,"rb") as f:h=f.read(16)
 if len(h)!=16 or h[:4]!=b"TGZ\0":continue
 _,unk,w,he=struct.unpack("<4sIii",h)
 if w==320 and he==1440:
  pan.append({"name":file.name,"sha256":__import__("hashlib").sha256(file.read_bytes()).hexdigest(),"length":file.stat().st_size})
report={"schema":"OpenZork.ConservatoryNativePanoramaHeaderInventory.v1",
 "source":"DATA2/ZASSETS/CONSERV","corpus_read_only":True,
 "tga_files":len(files),"panorama_320x1440_count":len(pan),"panoramas":pan}
out=r/"runtime-test"/"results"/"openzork-conserv-panorama-inventory-v6.json"
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"tga":len(files),"panoramas":len(pan),
                  "names":[p["name"] for p in pan[:120]],"report":str(out)}))
