"""V7 final non-destructive regression run: 25 legacy tests + project binding + hidden GUI guard.
Writes new report without touching historical v6/v7 regression evidence files.
"""
from datetime import datetime,timezone
from pathlib import Path
import subprocess,sys,json
from test_fidelity_runtime_regressions_v1 import TESTS,ROOT,CP
from fidelity_runtime_isolation_v1 import sha256
new=("test_fidelity_runtime_target_binding_v7.py",
     "test_fidelity_process_wide_preflight_v7.py")
tests=tuple(TESTS)+new
results=ROOT/"runtime-test"/"results"
old=[
 results/"fidelity-isolation-regressions-20261009.json",
 results/"fidelity-isolation-regressions-20261009-v7.json",
 results/"fidelity-isolation-regressions-20261009-v7-r2.json"
]
assert all(p.is_file() for p in old)
history={str(p):sha256(p) for p in old}
cases=[]
for name in tests:
 p=subprocess.run([sys.executable,"-B",str(CP/name)],cwd=str(CP),
                  capture_output=True,text=True,timeout=50)
 cases.append({"test":name,"status":"PASS" if p.returncode==0 else "FAIL",
   "exit_code":p.returncode,"stdout_tail":p.stdout[-680:],"stderr_tail":p.stderr[-900:]})
assert all(sha256(p)==history[str(p)] for p in old),"HISTORICAL_TEST_REPORT_DRIFT"
ok=all(x["status"]=="PASS" for x in cases)
report={
 "schema":"OpenRemaster.FidelityIsolationRegression.v7.r3",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":"PASS" if ok else "FAIL","count":len(cases),
 "passed":sum(x["status"]=="PASS" for x in cases),
 "contains_interactive_runtime_registry_checks":True,
 "contains_hidden_process_strict_preflight":True,
 "historical_reports_unchanged":True,
 "historic_hashes":history,
 "cases":cases,"original_game_fidelity":"NOT_TESTED"}
dest=results/"fidelity-isolation-regressions-20261009-v7-r3.json"
if dest.exists():raise RuntimeError("V7_R3_TEST_REPORT_ALREADY_EXISTS")
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"passed":report["passed"],
 "count":report["count"],"failures":[x for x in cases if x["status"]!="PASS"],
 "history_preserved":True,"report":str(dest)},ensure_ascii=False))
raise SystemExit(0 if ok else 1)
