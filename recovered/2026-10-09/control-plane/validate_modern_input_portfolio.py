import json,subprocess,sys
from pathlib import Path
root=Path(__file__).parent
validator=root/"validate_modern_input.py"
rows=[]
for p in sorted((root/"input-contracts").glob("*.json")):
 r=subprocess.run([sys.executable,str(validator),str(p)],capture_output=True,text=True)
 try: out=json.loads(r.stdout)
 except: out={"status":"FAIL","failures":["INVALID_VALIDATOR_OUTPUT"]}
 rows.append({"project":p.stem,"status":out.get("status"),"failures":out.get("failures",[])})
ok=all(x["status"]=="PASS" for x in rows)
print(json.dumps({"schema":"ModernInputPortfolioValidation.v1","status":"PASS" if ok else "FAIL","projects":rows},indent=2))
raise SystemExit(0 if ok else 1)
