"""Immutable v7 regression report; preserve previous v6 regression evidence file byte-for-byte.
Tests are imported from v6 suite, plus new source/EXE-target binding negatives.
"""
import json,subprocess,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
from test_fidelity_runtime_regressions_v1 import TESTS,ROOT,CP
from fidelity_runtime_isolation_v1 import sha256
tests=tuple(TESTS)+("test_fidelity_runtime_target_binding_v7.py",)
legacy=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009.json"
legacy_hash_before=sha256(legacy)
rows=[]
for f in tests:
    p=subprocess.run([sys.executable,"-B",str(CP/f)],
        cwd=str(CP),capture_output=True,text=True,timeout=45)
    rows.append({"test":f,"status":"PASS" if p.returncode==0 else "FAIL",
        "exit":p.returncode,"stdout_tail":p.stdout[-600:],
        "stderr_tail":p.stderr[-900:]})
legacy_hash_after=sha256(legacy)
if legacy_hash_before!=legacy_hash_after:
    raise AssertionError("V6_REGRESSION_EVIDENCE_CHANGED")
good=all(x["status"]=="PASS" for x in rows)
report={
 "schema":"OpenRemaster.FidelityIsolationRegression.v7",
 "timestamp_utc":datetime.now(timezone.utc).isoformat(),
 "status":"PASS" if good else "FAIL",
 "count":len(rows),"passed":sum(x["status"]=="PASS" for x in rows),
 "old_v6_regression_provenance_sha256":legacy_hash_before,
 "old_v6_regression_unchanged":True,
 "includes_target_binding_game_executable_and_config_tests":True,
 "cases":rows,
 "original_game_fidelity":"NOT_TESTED"}
target=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009-v7.json"
if target.exists():raise RuntimeError("V7_REGRESSION_REPORT_ALREADY_EXISTS")
target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"passed":report["passed"],
 "count":len(rows),"failures":[x for x in rows if x["status"]!="PASS"],
 "preserved_v6_hash":legacy_hash_before,
 "evidence":str(target)},ensure_ascii=False))
raise SystemExit(0 if good else 1)
