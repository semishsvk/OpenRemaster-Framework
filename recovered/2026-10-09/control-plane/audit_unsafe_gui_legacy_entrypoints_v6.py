"""Read-only bounded audit of legacy direct Win32 GUI actions in OpenRemaster project scripts.
Inventory is not an authorization to kill, rewrite, or execute those scripts.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import json,re
ROOT=Path(__file__).resolve().parents[2]
GROUPS={
 "global_focus":"SetForegroundWindow|SwitchToThisWindow|BringWindowToTop",
 "global_cursor":"SetCursorPos|mouse_event|SendInput|pyautogui\\.(?:moveTo|click|press)|win32api\\.SetCursorPos",
 "global_keyboard":"keybd_event|keyboard\\.press|PressKey\\(",
 "direct_gui_launch":"Start-Process|subprocess\\.Popen|CreateProcessW|os\\.startfile|\\bstart\\s+\\\"?(?:dosbox|scummvm|godot)",
 "raw_window_title":"FindWindow\\(|GetForegroundWindow\\(|\\bAlt\\+Tab\\b",
}
PATTERNS={kind:re.compile(pattern,re.I) for kind,pattern in GROUPS.items()}
folders=[
 ROOT/"work"/"OpenZork"/"tools",
 ROOT/"work"/"OpenZork"/"oracle-runtime",
 ROOT/"work"/"OpenZork"/"oracle-dosx",
 ROOT/"work"/"OpenAzrael"/"tools",
 ROOT/"orchestrator"/"control-plane",
]
results=[]
totals=Counter()
by_project=Counter()
for folder in folders:
 if not folder.is_dir():continue
 for file in folder.iterdir():
  if not file.is_file() or file.suffix.lower() not in (".py",".ps1",".cmd",".bat"):continue
  if file.stat().st_size>250_000:continue
  try:
   lines=file.read_text(encoding="utf-8-sig",errors="replace").splitlines()
  except OSError:continue
  hits=[]
  for i,line in enumerate(lines,1):
   stripped=line.strip()
   if not stripped or stripped.startswith("#") or stripped.startswith("//"):continue
   matched=[cat for cat,pat in PATTERNS.items() if pat.search(line)]
   if matched:
    hits.append({"line":i,"risk":matched,"sample":line[:180]})
    for k in matched:totals[k]+=1
  if hits:
   relative=str(file.relative_to(ROOT))
   results.append({"path":relative,"source_sha256":__import__("hashlib").sha256(file.read_bytes()).hexdigest(),
      "hits":hits[:30],"hit_count":len(hits)})
   by_project[file.parts[len(ROOT.parts)]]+=1
r={"schema":"OpenRemaster.UnmanagedGuiEntryPointAudit.v1",
 "created_utc":datetime.now(timezone.utc).isoformat(),"state":"READ_ONLY",
 "scanned_roots":[str(x) for x in folders],
 "affected_scripts":len(results),
 "categories":dict(totals),"by_top_level":dict(by_project),
 "risks":results,
 "legacy_scripts_mutated":False,"global_process_cleanup":False,
 "intended_action":"BLOCK_UNMANAGED_LAUNCH_THROUGH_ORCH_K003; DO_NOT_REWRITE_EVIDENCE_SCRIPTS"}
out=ROOT/"runtime-test"/"results"/"unmanaged-gui-entrypoint-audit-v6.json"
out.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":"READ_ONLY","affected_scripts":len(results),
 "category_matches":dict(totals),"by_top_level":dict(by_project),
 "sample":[{"path":x["path"],"categories":sorted(set(z for h in x["hits"] for z in h["risk"]))} for x in results[:26]],
 "report":str(out)},ensure_ascii=False))
