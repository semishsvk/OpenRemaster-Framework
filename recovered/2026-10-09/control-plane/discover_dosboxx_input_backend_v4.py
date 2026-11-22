"""Bounded local prior-art executable and input feature probe, read-only."""
from pathlib import Path
import os,json,subprocess
root=Path(__file__).resolve().parents[2]
roots=[root/"source",root/"tools",root/"work"/"OpenZork",Path(r"F:\OpenRemaster")]
matches=[]
walked=0
for r in roots:
 if not r.is_dir():continue
 for where,dirs,files in os.walk(r):
  walked+=1
  dirs[:]=[x for x in dirs if x.lower() not in
      {".git",".godot","assets","extracted","data1","data2","data3","venv","node_modules","build","builds","output","capture","captures"}]
  for f in files:
   if f.lower() in ("dosbox-x.exe","dosbox.exe","dosbox-staging.exe","dosbox-x-sdl2.exe"):
    matches.append({"path":str(Path(where)/f),"name":f})
  if walked>7500:break
 if walked>7500:break
print(json.dumps({"schema":"OpenRemaster.DOSBoxPriorArtInputBackendProbe.v1","directories_scanned":walked,
  "executables":matches[:40],"potential_preexisting_autotype":str(root/"work"/"OpenZork"/"oracle-dosx"/"zork-debug-autotype-r.conf"),
  "status":"READ_ONLY"},ensure_ascii=False))
