"""Read-only installed ScummVM capability probe: find saved-slot launch flag."""
import subprocess,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
exe=root/"source"/"Zork Grand Inquisitor"/"scummvm"/"scummvm.exe"
p=subprocess.run([str(exe),"--help"],capture_output=True,text=True,timeout=15)
out=p.stdout.splitlines()
hits=[(i+1,line) for i,line in enumerate(out) if any(w in line.lower() for w in ("slot","load","save","record"))]
print(json.dumps({"schema":"OpenZork.ScummVMSavedStatePriorArt.v1","exit":p.returncode,
  "help_matches":hits[:30],"supported_game_title":"Zork Nemesis","program":str(exe),
  "fidelity_authority":"SCUMMVM_CROSS_VALIDATION_NOT_NATIVE_DOS"}))
