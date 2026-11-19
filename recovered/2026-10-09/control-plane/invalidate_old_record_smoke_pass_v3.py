"""Non-destructive correction of a previous falsely accepted diagnostic capture.
Historical worker receipt remains intact; separate evidence refutes technical PASS.
"""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).resolve().parents[2]
target=root/"runtime-test"/"results"/"openzork-legacy-record-smoke-77df5799e1"
legacy=target/"legacy-bridge-report.json"
runtime=target/"result.json"
assert legacy.is_file() and runtime.is_file()
a=json.loads(legacy.read_text());r=json.loads(runtime.read_text())
assert r["exit_code"]==3221225477 and a["technical_capture_pass"] is True, "No known prior false positive to correct"
b={"schema":"OpenRemaster.HistoricalDiagnosticInvalidation.v1",
   "date_utc":datetime.now(timezone.utc).isoformat(),
   "supersedes_only_claim":"LegacyGUIMigratedReceipt.v1 TECHNICAL_DIAGNOSTIC_PASS of this single run",
   "record_id":target.name,
   "status":"TECHNICAL_DIAGNOSTIC_PASS_REVOKED_ABNORMAL_RUNTIME_EXIT",
   "exit_code_decimal":r["exit_code"],"exit_code_hex":hex(r["exit_code"]),
   "legacy_receipt_sha256":hashlib.sha256(legacy.read_bytes()).hexdigest(),
   "worker_result_sha256":hashlib.sha256(runtime.read_bytes()).hexdigest(),
   "capture_files":"PRESERVED_FOR_DIAGNOSTICS_NOT_FIDELITY",
   "fidelity_acceptance":"NEVER_GRANTED",
   "new_gate":"RUNTIME_EXIT_CODE_ZERO_REQUIRED",
   "historical_receipt_modified":False}
out=target/"technical-pass-invalidation-v3.json"
out.write_text(json.dumps(b,indent=2),encoding="utf-8")
print(json.dumps({"status":b["status"],"record_id":b["record_id"],"attestation":str(out)}))
