"""Read-only CLI target listing from ScummVM using canonical and private INI paths."""
from pathlib import Path
import subprocess,json
r=Path(__file__).resolve().parents[2]
exe=r/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
confs=[
r/"work"/"OpenZork"/"oracle-runtime"/"scummvm.ini",
r/"runtime-test"/"results"/"openzork-supervised-oracle-passive-80efcbbbd"/"fidelity-isolated"/"config"/"scummvm.ini",
r/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"scummvm.ini"
]
rows=[]
for cfg in confs:
 if not cfg.is_file():
  rows.append({"config":str(cfg),"error":"MISSING"});continue
 for name,argv in [
 ("list-targets",[str(exe),"--config="+str(cfg),"--list-targets"]),
 ("help",[str(exe),"--config="+str(cfg),"--help"])
 ]:
  try:
   p=subprocess.run(argv,capture_output=True,text=True,timeout=8)
   rows.append({"config":str(cfg),"kind":name,"exit":p.returncode,"stdout":p.stdout[:950],"stderr":p.stderr[:700]})
  except Exception as e:rows.append({"config":str(cfg),"kind":name,"error":type(e).__name__+":"+str(e)})
print(json.dumps(rows,ensure_ascii=False))
