from pathlib import Path
p=Path(r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um\windows.graphics.directx.direct3d11.interop.h")
text=p.read_text(errors="replace").splitlines()
for i,line in enumerate(text):
 if "IDirect3DDxgiInterfaceAccess" in line or "namespace" in line:
  print(i+1, line[:150])
