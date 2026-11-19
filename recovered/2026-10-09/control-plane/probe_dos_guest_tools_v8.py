"""Read-only compiler/assembler and DOSBox-X integration device configuration survey."""
import os,subprocess,shutil,json,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[2]
dosx=Path(r"F:\OpenRemaster\work\OpenROTH\tools\dosbox-x-2026.10.01\portable\mingw-build\mingw")
config=(dosx/"dosbox-x.reference.full.conf").read_text(encoding="utf-8-sig",errors="replace").splitlines()
hits=[{"line":i+1,"text":row.strip()[:200]} for i,row in enumerate(config)
      if any(s in row.lower() for s in ("integration device","mouse_emulation","mcp_server","debugbox"))]
paths=[R/"tools",Path(r"C:\Program Files (x86)"),Path(r"C:\Program Files"),R/"orchestrator"/"native-worker"/"runtime"/"Scripts"]
found=[]
names={"nasm.exe","yasm.exe","fasm.exe","wasm.exe","owcc.exe","wcc.exe","wcl.exe","tasm.exe","ml.exe","ml64.exe","as.exe","ld.exe","bcc.exe"}
total_dirs=0
for root in paths:
 if not root.is_dir():continue
 for base,dirs,files in os.walk(root):
  total_dirs+=1
  dirs[:]=[d for d in dirs if d.lower() not in {".git","node_modules",".godot","packages","windowsapps","cache","tmp","temp","fonts","assets","output"}]
  for f in files:
   if f.lower() in names:found.append(str(Path(base)/f))
  if total_dirs>5500:break
 if total_dirs>5500:break
print(json.dumps({"status":"READ_ONLY","assemblertools":[{"name":n,"resolved_path":shutil.which(n)} for n in ("nasm","yasm","ml","ml64","as","gcc","clang","fasm","wcl")],
 "interesting_files":found[:35],"search_dirs":total_dirs,"python_modules":{n:bool(importlib.util.find_spec(n)) for n in ("keystone","capstone","unicorn")},
 "integration_device_config":[x for x in hits if "integration device" in x["text"].lower()][:12],
 "debugbox_config":[x for x in hits if "mcp_server" in x["text"].lower()][:12]},ensure_ascii=False))
