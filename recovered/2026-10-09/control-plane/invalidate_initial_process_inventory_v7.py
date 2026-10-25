"""Append-only correction for empty initial process discovery due to PowerShell regex escaping.
Do not rewrite original report; supersede with verified WMI -like selector r2.
"""
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2]
base=R/"runtime-test"/"results"
bad=base/"fidelity-process-wide-contamination-audit-v7.json"
fixed=base/"fidelity-process-wide-contamination-audit-v7-r2.json"
assert bad.is_file() and fixed.is_file()
o=json.loads(bad.read_text(encoding="utf-8-sig"))
n=json.loads(fixed.read_text(encoding="utf-8-sig"))
assert o["candidate_GUI_process_count"]==0
assert n["relevant_GUI_PIDs"]>=1
assert n["visible_game_window_count"]>=n["relevant_GUI_PIDs"]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={
 "schema":"OpenRemaster.ProcessAuditSupersession.v1",
 "date_utc":datetime.now(timezone.utc).isoformat(),
 "status":"INITIAL_ZERO_PROCESS_REPORT_INVALID_SUPERSEDED_BY_R2",
 "invalidated_audit_path":str(bad),
 "invalidated_audit_sha256":sha(bad),
 "reason":"Powershell regex escaping made process-name filter falsely return zero",
 "superseding_audit_path":str(fixed),
 "superseding_audit_sha256":sha(fixed),
 "superseding_active_gui_pids":n["relevant_GUI_PIDs"],
 "original_audit_overwritten":False,
 "no_game_process_changed":True}
dest=base/"fidelity-process-audit-supersession-v7.json"
if dest.exists():raise RuntimeError("SUPERSESSION_RECORD_ALREADY_EXISTS")
dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"pids":report["superseding_active_gui_pids"],
 "evidence":str(dest)},ensure_ascii=False))
