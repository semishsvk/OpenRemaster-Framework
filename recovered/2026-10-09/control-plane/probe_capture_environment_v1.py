import importlib.util, json, os, platform, shutil, subprocess
from pathlib import Path
from fidelity_runtime_isolation_v1 import gui_conflicts, process_session, active_console_session
def run(argv, timeout=15):
 try:
  p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout)
  return {"code":p.returncode,"stdout":p.stdout[-2800:],"stderr":p.stderr[-400:]}
 except Exception as e: return {"error":type(e).__name__,"detail":str(e)}
cands=[
 r"C:\Program Files (x86)\Windows Kits\10\UnionMetadata",
 r"C:\Program Files (x86)\Windows Kits\10\References",
 r"C:\Program Files (x86)\Windows Kits\10\bin",
 r"C:\Program Files\dotnet\packs",
 r"C:\Program Files\dotnet\sdk",
 r"C:\Program Files\WindowsApps",
]
w=gui_conflicts()
out={"schema":"OpenRemaster.CaptureEnvironmentProbe.v1","os":platform.platform(),"python":platform.python_version(),"session":process_session(os.getpid()),"console":active_console_session(),"ffmpeg":shutil.which("ffmpeg"),"dotnet":shutil.which("dotnet"),"packages":{p:bool(importlib.util.find_spec(p)) for p in ("winrt","win32gui","win32process","comtypes","PIL","numpy","mss","windows_capture","ctypes")}, "known_locations":{p:{"exists":Path(p).exists(),"children":sorted(x.name for x in Path(p).iterdir())[:18] if Path(p).is_dir() else []} for p in cands},"dotnet_info":run(["dotnet","--list-sdks"]),"ffmpeg_devices":run(["ffmpeg","-hide_banner","-devices"]),"gui":{"window_count":len(w),"pids":len(set(x["pid"] for x in w)),"titles":[(x["pid"],x["title"]) for x in w[:14]]}}
p=Path(__file__).parents[2]/"runtime-test"/"results"/"capture-environment-20261009.json"
p.write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps({"status":"AUDITED","packages":out["packages"],"known_locations":out["known_locations"],"gui":out["gui"],"dotnet":out["dotnet_info"],"report":str(p)},ensure_ascii=False))
