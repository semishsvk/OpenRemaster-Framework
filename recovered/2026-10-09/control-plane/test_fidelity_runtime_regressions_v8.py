"""V8 non-destructive regression: core v7 suite plus native guest input
cursor guard, clipped-left feedback, bounded capture v2, exact TCP peer PID
and original r9 stable courtyard evidence/negative controls.
No original game GUI launched by regression, historical reports never overwritten.
"""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,hashlib
from test_fidelity_runtime_regressions_v1 import TESTS,ROOT,CP
from fidelity_runtime_isolation_v1 import sha256
extra=[
 "test_fidelity_runtime_target_binding_v7.py",
 "test_fidelity_process_wide_preflight_v7.py",
 "test_capture_schedule_v2_v8.py",
 "test_original_newgame_cursor_gate_v8.py",
 "test_native_cursor_feedback_v8.py",
 "test_mcp_tcp_peer_attestation_v8.py",
 "test_native_zork_r9_replay_gate_v8.py"
]
tests=list(TESTS)+extra
assert len(tests)==32,(len(tests),tests)
old=[
 ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009.json",
 ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009-v7-r3.json",
 ROOT/"runtime-test"/"results"/"fidelity-runtime-isolation-checkpoint-20261009-v7.json"
]
frozen={str(p):sha256(p) for p in old}
cases=[]
for name in tests:
 file=CP/name
 assert file.is_file(),str(file)
 p=subprocess.run([sys.executable,"-B",str(file)],
  cwd=str(CP),capture_output=True,text=True,timeout=55)
 cases.append({"test":name,"exit_code":p.returncode,
  "status":"PASS" if p.returncode==0 else "FAIL",
  "stdout_tail":p.stdout[-650:],"stderr_tail":p.stderr[-1000:]})
assert all(sha256(p)==frozen[str(p)] for p in old),"IMMUTABLE_V7_EVIDENCE_CHANGED"
passed=sum(x["status"]=="PASS" for x in cases)
record={
 "schema":"OpenRemaster.FidelityIsolationRegression.v8",
 "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"PASS" if passed==len(tests) else "FAIL",
 "count":len(tests),"passed":passed,
 "historical_v7_and_v6_reports_unchanged":True,
 "frozen_historical_sha256":frozen,
 "cases":cases,
 "no_original_game_runtimes_launched_by_suite":True,
 "original_vs_candidate_gameplay_fidelity":"NOT_VERIFIED"
}
target=ROOT/"runtime-test"/"results"/"fidelity-isolation-regressions-20261009-v8.json"
if target.exists():raise RuntimeError("V8_REGRESSION_REPORT_EXISTS_NO_OVERWRITE")
target.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"tests_passed":passed,
"tests_total":len(cases),
"failed":[x for x in cases if x["status"]!="PASS"],
"historical_reports_untouched":True,"report":str(target)},ensure_ascii=False))
raise SystemExit(0 if passed==len(tests) else 1)
