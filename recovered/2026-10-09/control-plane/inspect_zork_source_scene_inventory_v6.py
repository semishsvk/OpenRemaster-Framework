"""Read-only targeted inventory of Zork game assets and OpenZork extracted panorama families."""
from pathlib import Path
import json,collections
R=Path(__file__).resolve().parents[2]
folders=[
 R/"source"/"Zork Nemesis"/"DATA1"/"ZASSETS",
 R/"source"/"Zork Nemesis"/"DATA2",
 R/"work"/"OpenZork"/"runtime"/"assets",
 R/"work"/"OpenZork"/"runtime"/"assets"/"panoramas_hd",
 R/"work"/"OpenZork"/"panorama_lab",
]
out=[]
for folder in folders:
 row={"root":str(folder),"exists":folder.is_dir()}
 if folder.is_dir():
  files=[p for p in folder.iterdir() if p.is_file()]
  row["immediate_files"]=len(files)
  row["immediate_subdirs"]=[p.name for p in folder.iterdir() if p.is_dir()][:70]
  row["extensions"]=dict(collections.Counter(p.suffix.lower() for p in files))
  row["file_names"]=[p.name for p in files[:80]]
 out.append(row)
z=R/"source"/"Zork Nemesis"/"DATA1"/"ZASSETS"
if z.is_dir():
 for folder in sorted(p for p in z.iterdir() if p.is_dir()):
  names=[p.name for p in folder.iterdir() if p.is_file()]
  out.append({"folder":folder.name,"file_count":len(names),"sample_tga":[x for x in names if x.lower().endswith(".tga")][:20],
              "extensions":dict(collections.Counter(Path(x).suffix.lower() for x in names))})
p=R/"runtime-test"/"results"/"openzork-source-scene-inventory-v6.json"
p.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"roots":out[:5],"scene_folders":out[5:],"report":str(p)},ensure_ascii=False))
