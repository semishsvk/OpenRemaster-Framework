from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parent
source=root/"synthetic_scummvm_oracle.cpp"
exe=root/"synthetic_scummvm_oracle.exe"
bat=root/"build.cmd"
vc=Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat")
bat.write_text(f'@echo off\ncall "{vc}" >nul\ncl /nologo /std:c++20 /EHsc /O2 /W4 /utf-8 /MD /Fe:"{exe}" "{source}" /link /SUBSYSTEM:WINDOWS\nexit /b %errorlevel%\n',encoding="ascii")
p=subprocess.run(["cmd.exe","/d","/c",str(bat)],cwd=str(root),capture_output=True,text=True,timeout=120)
report={"schema":"OpenRemaster.PassiveFixtureBuild.v1","status":"PASS" if p.returncode==0 and exe.is_file() else "FAIL","stdout":p.stdout,"stderr":p.stderr}
if exe.is_file():report["sha256"]=hashlib.sha256(exe.read_bytes()).hexdigest()
(root/"build-evidence.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"status":report["status"],"sha256":report.get("sha256"),"stdout_tail":p.stdout[-1000:],"stderr_tail":p.stderr[-1000:]}))
raise SystemExit(0 if report["status"]=="PASS" else 1)
