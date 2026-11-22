from pathlib import Path
from collections import Counter
import json
r=Path(__file__).resolve().parents[2]/"work"/"OpenZork"/"runtime"
ext=Counter();sizes=Counter()
for p in r.rglob("*"):
 if not p.is_file():continue
 if ".godot" in p.parts:continue
 ext[p.suffix.lower()]+=1;sizes[p.suffix.lower()]+=p.stat().st_size
print(json.dumps({"root":str(r),"files_excluding_dotgodot":sum(ext.values()),
"total_megabytes":round(sum(sizes.values())/1048576,2),
"counts":dict(ext),"bytes_by_extension":dict(sizes)}))
