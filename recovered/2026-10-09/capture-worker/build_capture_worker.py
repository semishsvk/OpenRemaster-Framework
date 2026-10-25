import subprocess, json, hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
src=root/"capture_window_wgc.cpp"
build=root/"build"
build.mkdir(exist_ok=True)
exe=root/"capture_window_wgc.exe"
vs=Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat")
cmd=f'call "{vs}" >nul\ncl /nologo /std:c++20 /EHsc /O2 /W4 /utf-8 /MD /Fe:"{exe}" "{src}" /link'
batch=root/"build-capture.cmd"
batch.write_text("@echo off\n"+cmd+"\nexit /b %errorlevel%\n",encoding="ascii")
p=subprocess.run(["cmd.exe","/d","/c",str(batch)],cwd=str(build),text=True,capture_output=True,timeout=120)
out={"exit":p.returncode,"command":cmd,"stdout":p.stdout,"stderr":p.stderr,"executable_exists":exe.is_file()}
if exe.is_file():out["exe_sha256"]=hashlib.sha256(exe.read_bytes()).hexdigest()
(root/"build-log.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"exit":out["exit"],"stdout_tail":p.stdout[-6000:],"stderr_tail":p.stderr[-4000:],"exe":str(exe),"exe_sha256":out.get("exe_sha256")}))
raise SystemExit(p.returncode)
