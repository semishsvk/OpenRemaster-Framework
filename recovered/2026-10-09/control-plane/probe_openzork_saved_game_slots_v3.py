from pathlib import Path
import subprocess,json,hashlib
r=Path(__file__).resolve().parents[2]
exe=r/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
cfg=r/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini"
saves=r/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"saves"
p=subprocess.run([str(exe),"--config="+str(cfg),"--savepath="+str(saves),"--list-saves=znemesis"],capture_output=True,text=True,timeout=12)
manifest=[]
for f in saves.iterdir():
 if f.is_file():
  h=hashlib.sha256(f.read_bytes()).hexdigest()
  manifest.append({"name":f.name,"size":f.stat().st_size,"sha256":h})
print(json.dumps({"status":"READ_ONLY","exit":p.returncode,"stdout":p.stdout[-2400:],"stderr":p.stderr[-500:],"files":manifest}))
