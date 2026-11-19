import os,json,glob,subprocess,shutil
from pathlib import Path
p=lambda s:Path(s)
bases=[r"C:\Program Files\Microsoft Visual Studio\2022",r"C:\Program Files\Microsoft Visual Studio\2026",r"C:\Program Files (x86)\Microsoft Visual Studio\2019",r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0",r"C:\Program Files (x86)\Windows Kits\10\UnionMetadata\10.0.26100.0",r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64"]
wanted=[r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\cppwinrt\winrt\Windows.Graphics.Capture.h",r"C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0\um\windows.graphics.capture.interop.h",r"C:\Program Files (x86)\Windows Kits\10\UnionMetadata\10.0.26100.0\Windows.winmd",r"C:\Program Files\dotnet\packs\Microsoft.Windows.SDK.NET.Ref",r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\cppwinrt.exe"]
vswhere=r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe"
vscmd=subprocess.run([vswhere,"-latest","-products","*","-property","installationPath"],capture_output=True,text=True) if p(vswhere).is_file() else None
print(json.dumps({"bases":{q:{"exists":p(q).exists(),"children":[x.name for x in p(q).iterdir()][:12] if p(q).is_dir() else []} for q in bases},
 "wanted":{q:p(q).exists() for q in wanted},"vswhere":vscmd.stdout if vscmd else "not installed","where":{q:shutil.which(q) for q in ("cl","clang-cl","clang++","g++","cppwinrt","csc","msbuild","dotnet")}},indent=2))
