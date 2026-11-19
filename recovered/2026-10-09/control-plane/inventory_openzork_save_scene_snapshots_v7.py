"""Read-only bounded inventory of ScummVM Zork saves across project work and evidence.
Only metadata, LOC scene/view and hashes. Do not open any GUI or modify saves.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,struct,json,os,re
R=Path(__file__).resolve().parents[2]
roots=[
 R/"work"/"OpenZork"/"oracle",
 R/"work"/"OpenZork"/"oracle-runtime",
 R/"work"/"OpenZork"/"oracle-dos",
 R/"work"/"OpenZork"/"oracle-dosx",
 R/"work"/"OpenZork"/"staging",
 R/"output"/"projects"/"OpenZork"/"evidence",
 R/"runtime-test"/"results",
]
names=re.compile(r"(?i)^znemesis\.\d{3}$")
exclusions={".godot",".git","node_modules","_pycache_","assets","extracted","raw_assets","data1","data2","data3","src","builds"}
data=[];folders_seen=0
for root in roots:
 if not root.is_dir():continue
 for path,dirs,files in os.walk(root):
  folders_seen+=1
  dirs[:]=[x for x in dirs if x.lower() not in exclusions]
  for filename in files:
   if not names.fullmatch(filename):continue
   file=Path(path)/filename
   try:
    stat=file.stat()
    if not 28<=stat.st_size<=8*1024*1024:continue
    b=file.read_bytes()
    if b[:4]==b"ZNSG" and b[12:16]==b"LOC " and len(b)>=28:
     scene=b[20:24].decode("ascii","replace")
     pos=struct.unpack_from("<I",b,24)[0]
     ver=struct.unpack_from("<I",b,4)[0]
    else:scene=None;pos=None;ver=None
    data.append({
      "path":str(file),"name":filename,"bytes":len(b),
      "sha256":hashlib.sha256(b).hexdigest(),
      "scene":scene,"view":pos,"version":ver,
      "mtime_utc":datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),
      "under_readonly_pinned_evidence":"VB30-SEED-PINNED" in str(file)
    })
   except (OSError,ValueError,struct.error):continue
  if folders_seen>14000:break
 if folders_seen>14000:break
group=Counter(f"{x['scene']}@{x['view']}" for x in data)
result={
 "schema":"OpenZork.SavedStateScenePoseInventory.v1",
 "status":"READ_ONLY",
 "captured_at":datetime.now(timezone.utc).isoformat(),
 "scanned_directories":folders_seen,
 "save_file_count":len(data),
 "unique_content_hashes":len({x["sha256"] for x in data}),
 "scene_pose_distribution":dict(group),
 "items":data
}
out=R/"runtime-test"/"results"/"openzork-save-scene-pose-inventory-v7.json"
if out.exists():raise RuntimeError("INVENTORY_EXISTS")
out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"READ_ONLY","files":len(data),"unique_sha":result["unique_content_hashes"],
 "locations":dict(group),"possible_VB20":[x for x in data if x["scene"] in ("vb20","VB20")][:12],
 "possible_VB30_364":[x for x in data if x["scene"] in ("vb30","VB30") and x["view"]!=1058][:12],
 "report":str(out)},ensure_ascii=False))
