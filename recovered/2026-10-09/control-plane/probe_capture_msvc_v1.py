import json
from pathlib import Path
v=Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise")
paths=[
v/r"VC\Auxiliary\Build\vcvars64.bat",
v/r"VC\Tools\MSVC",
v/r"Common7\Tools\VsDevCmd.bat",
]
x={}
for q in paths:
 x[str(q)]={"exists":q.exists(),"children":sorted(f.name for f in q.iterdir())[:8] if q.is_dir() else []}
if paths[1].is_dir():
 for vc in paths[1].iterdir():
  q=vc/r"bin\Hostx64\x64\cl.exe"
  x[str(q)]={"exists":q.exists()}
print(json.dumps(x,indent=2))
