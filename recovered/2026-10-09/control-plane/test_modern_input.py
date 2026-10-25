import json,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).parent
validator=root/"validate_modern_input.py"
good=root/"input-contracts"/"OpenUnderworld.json"
a=subprocess.run([sys.executable,str(validator),str(good)],capture_output=True,text=True)
bad=json.loads(good.read_text(encoding="utf-8")); bad["test_backend"]["host_coordinate_independent"]=False
with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False,encoding="utf-8") as f:
 json.dump(bad,f); bp=f.name
b=subprocess.run([sys.executable,str(validator),bp],capture_output=True,text=True)
ok=a.returncode==0 and b.returncode!=0 and "HOST_COORDINATE_DEPENDENT" in b.stdout
print(json.dumps({"schema":"ModernInputCanary.v1","status":"PASS" if ok else "FAIL","positive":a.returncode,"negative":b.returncode},indent=2))
raise SystemExit(0 if ok else 1)
