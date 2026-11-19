"""Complete rerun following v7 canary reentrancy fix.
Preserves v6 report and previously FAILED v7 report; writes unique r2 evidence.
"""
import subprocess,sys,json
from pathlib import Path
from datetime import datetime,timezone
from test_fidelity_runtime_regressions_v1 import TESTS,ROOT,CP
from fidelity_runtime_isolation_v1 import sha256
tests=tuple(TESTS)+("test_fidelity_runtime_target_binding_v7.py",)
v6=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009.json"
previous=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009-v7.json"
v6hash=sha256(v6)
prevhash=sha256(previous)
rows=[]
for name in tests:
 p=subprocess.run([sys.executable,"-B",str(CP/name)],cwd=str(CP),
     capture_output=True,text=True,timeout=45)
 rows.append({"case":name,"status":"PASS" if p.returncode==0 else "FAIL",
    "exit_code":p.returncode,
    "stdout_tail":p.stdout[-650:],"stderr_tail":p.stderr[-1000:]})
assert sha256(v6)==v6hash and sha256(previous)==prevhash
good=all(x["status"]=="PASS" for x in rows)
report={
 "schema":"OpenRemaster.FidelityIsolationRegression.v7.r2",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":"PASS" if good else "FAIL",
 "count":len(rows),
 "passed":sum(x["status"]=="PASS" for x in rows),
 "v6_historical_regression_hash_preserved":v6hash,
 "v7_initial_failure_hash_preserved":prevhash,
 "registry_sha256":sha256(CP/"fidelity-runtime-target-registry.v7.json"),
 "cases":rows,
 "original_game_fidelity":"NOT_TESTED"}
out=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009-v7-r2.json"
if out.exists():raise RuntimeError("R2_REGRESSION_REPORT_ALREADY_EXISTS")
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"passed":report["passed"],
 "count":report["count"],"failures":[r for r in rows if r["status"]!="PASS"],
 "historical_reports_preserved":True,"evidence":str(out)},ensure_ascii=False))
raise SystemExit(0 if good else 1)
