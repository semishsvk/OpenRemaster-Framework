"""Read-only CLI/cwd check to explain why private ScummVM opens launcher."""
import subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
exe=root/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
run=root/"runtime-test"/"results"/"openzork-supervised-oracle-passive-80efcbbbd"/"fidelity-isolated"
cfg=run/"config"/"scummvm.ini"
rows=[]
for cwd in (exe.parent,run):
 for option in ("--list-games","--list-targets"):
  p=subprocess.run([str(exe),"--config="+str(cfg),option],cwd=str(cwd),
                   capture_output=True,text=True,timeout=10)
  rows.append({"cwd":str(cwd),"option":option,"exit":p.returncode,
               "znemesis_supported":("Zork Nemesis" in p.stdout),
               "output_tail":p.stdout[-320:],"stderr_tail":p.stderr[-500:]})
print(json.dumps(rows))
