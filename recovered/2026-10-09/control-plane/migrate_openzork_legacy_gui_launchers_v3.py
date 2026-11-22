"""Migrate precisely two known OpenZork direct GUI starters to ORCH-K003 bridge.
Immutable backup of originals; no game launched; no canonical source edited.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os
root=Path(__file__).resolve().parents[2]
old_dir=root/"work"/"OpenZork"/"oracle-runtime"
backup=root/"orchestrator"/"backups"/"openzork-legacy-gui-launchers-20261009-v3"
backup.mkdir(parents=True,exist_ok=True)
records=[]
for name,task in [("launch-smoke.ps1","launch-smoke"),("record-smoke.ps1","record-smoke")]:
 src=old_dir/name
 assert src.is_file(),str(src)
 original=src.read_bytes()
 archived=backup/name
 if not archived.exists():
  assert b"Start-Process" in original, "Legacy source did not match expected launcher"
  archived.write_bytes(original)
 assert archived.exists()
 old_hash=hashlib.sha256(archived.read_bytes()).hexdigest()
 wrapper=f"""# OpenRemaster.LegacyGUIBridge.v3 — no direct GUI subprocess launch.
# Default strict admission will fail CLOSED if another GUI runtime occupies HomePC.
# -PassiveDiagnostic explicitly requests a non-fidelity technical-only capture.
param([switch]$PassiveDiagnostic,[switch]$DryRun)
$ErrorActionPreference = 'Stop'
$RuntimePython = 'F:\\Remaster Framework\\orchestrator\\native-worker\\runtime\\python.exe'
$Bridge = 'F:\\Remaster Framework\\orchestrator\\control-plane\\fidelity_legacy_launcher_bridge_v3.py'
if(-not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) {{ throw 'Missing OpenRemaster local Python worker' }}
if(-not (Test-Path -LiteralPath $Bridge -PathType Leaf)) {{ throw 'Missing canonical ORCH-K003 bridge' }}
$Argv = @('-B', $Bridge, '--task', '{task}')
if($PassiveDiagnostic) {{ $Argv += '--passive-diagnostic' }}
if($DryRun) {{ $Argv += '--dry-run' }}
& $RuntimePython @Argv
exit $LASTEXITCODE
"""
 data=wrapper.encode("utf-8")
 tmp=src.with_suffix(".ps1.fidelity-v3.tmp")
 tmp.write_bytes(data)
 os.replace(tmp,src)
 new_hash=hashlib.sha256(src.read_bytes()).hexdigest()
 assert b"Start-Process" not in src.read_bytes()
 records.append({"name":name,"task":task,"original_sha256":old_hash,"wrapper_sha256":new_hash,
                 "backup":str(archived),"active":str(src)})
report={"schema":"OpenRemaster.OpenZorkLegacyGUIEntryPointMigration.v3",
        "status":"APPLIED","date_utc":datetime.now(timezone.utc).isoformat(),
        "migration_scope":"OpenZork oracle-runtime two interactive .ps1 launchers only",
        "canonical_game_source":"UNCHANGED","created_gui_processes":0,
        "setup_target_cmd":"UNCHANGED_CLI_METADATA_ONLY",
        "strict_fidelity_default":"GLOBAL_LEASE_AND_FOREIGN_GUI_FAIL_CLOSED",
        "passive_explicit":"DIAGNOSTIC_CAPTURE_ONLY_NEVER_FIDELITY_PASS",
        "records":records}
out=backup/"migration-receipt.json"
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps({"status":"APPLIED","migrated":len(records),"archive":str(backup),
                  "details":[{"name":x["name"],"old_hash":x["original_sha256"],"new_hash":x["wrapper_sha256"]} for x in records]}))
