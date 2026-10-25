"""Read-only report of direct GUI launchers across game workspaces; bounded input."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import json,re
root=Path(__file__).resolve().parents[2]
work=root/"work"
exts={".ps1",".cmd",".bat",".py"}
terms=re.compile(r"(?i)(dosbox(?:-x)?(?:\.exe)?|scummvm(?:\.exe)?|Godot_v\d|--no-fullscreen|Start-Process|Popen\(|subprocess\.run\(|os\.startfile|start\s+\"?[^\"\s]*(?:godot|dosbox))")
entries=[]
max_bytes=600_000
for project in sorted(p for p in work.iterdir() if p.is_dir() and p.name not in ("_recovery","_reviews","_staging")):
 # Enumerate select directories only; avoid recursive asset/source distributions and huge vendor trees.
 candidates=[]
 for folder in (project,project/"oracle",project/"oracle-runtime",project/"tools",project/"scripts",project/"staging"):
  if not folder.is_dir():continue
  for file in folder.iterdir():
   if file.is_file() and file.suffix.lower() in exts and file.stat().st_size<max_bytes:
    candidates.append(file)
 for f in candidates:
  try: lines=f.read_text(encoding="utf-8-sig",errors="replace").splitlines()
  except OSError:continue
  hits=[{"line":i+1,"text":line[:280]} for i,line in enumerate(lines) if terms.search(line)]
  if hits:entries.append({"project":project.name,"relative_path":str(f.relative_to(root)),"hits":hits[:15],"total_hits":len(hits)})
report={"schema":"OpenRemaster.LegacyGuiLaunchInventory.v1","date_utc":datetime.now(timezone.utc).isoformat(),
"status":"READ_ONLY","scanned_exts":list(exts),"entries":entries}
dest=root/"runtime-test"/"results"/"legacy-gui-launcher-inventory-v3.json"
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"READ_ONLY","items":len(entries),
 "projects":dict(Counter(e["project"] for e in entries)),
 "openzork":[e for e in entries if e["project"]=="OpenZork"][:18],
 "report":str(dest)},ensure_ascii=False))
