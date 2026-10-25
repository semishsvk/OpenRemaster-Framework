import subprocess,json,hashlib
from pathlib import Path
root=Path(__file__).parent
src=root/"capture_process_audio.cpp"
exe=root/"capture_process_audio.exe"
build=root/"build"
vs=Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat")
batch=root/"build-audio.cmd"
batch.write_text(f'@echo off\ncall "{vs}" >nul\ncl /nologo /std:c++20 /EHsc /O2 /W4 /utf-8 /MD /Fe:"{exe}" "{src}" /link\nexit /b %errorlevel%\n',encoding="ascii")
p=subprocess.run(["cmd.exe","/d","/c",str(batch)],cwd=str(build),capture_output=True,text=True,timeout=120)
report={"status":"PASS" if p.returncode==0 else "FAIL","exit":p.returncode,"stdout":p.stdout,"stderr":p.stderr,"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest()}
if p.returncode==0 and exe.is_file():report["exe_sha256"]=hashlib.sha256(exe.read_bytes()).hexdigest()
(root/"audio-build-log.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"status":report["status"],"exit":p.returncode,"stdout_tail":p.stdout[-5500:],"stderr_tail":p.stderr[-1500:],"exe_sha256":report.get("exe_sha256")}))
raise SystemExit(p.returncode)
