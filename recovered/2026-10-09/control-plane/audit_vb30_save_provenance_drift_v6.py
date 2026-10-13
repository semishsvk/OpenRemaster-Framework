"""Read-only provenance drift audit; never overwrite a changed save or recast it as canonical."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]
paths=[
 R/"work"/"OpenZork"/"staging"/"20261009-R10R3-NEGATIVE-FIDELITY"/"oracle_session"/"saves"/"znemesis.000",
 R/"work"/"OpenZork"/"oracle-runtime"/"saves"/"znemesis.000",
 R/"runtime-test"/"results"/"openzork-scummvm-seeded-scene-8938d2e819"/"fidelity-isolated"/"saves"/"znemesis.000",
 R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"/"fidelity-isolated"/"saves"/"znemesis.000"
]
rows=[]
for p in paths:
 if not p.is_file():
  rows.append({"path":str(p),"exists":False});continue
 stat=p.stat()
 b=p.read_bytes()
 scene=None;view=None
 if b.startswith(b"ZNSG") and b[12:16]==b"LOC " and len(b)>27:
  import struct
  scene=b[20:24].decode("ascii","replace")
  view=struct.unpack_from("<I",b,24)[0]
 rows.append({"path":str(p),"exists":True,"bytes":len(b),
 "sha256":hashlib.sha256(b).hexdigest(),
 "mtime_utc":datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),
 "scene":scene,"view":view})
expected="3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc"
report={"schema":"OpenZork.SaveSeedProvenanceDriftAudit.v1","date_utc":datetime.now(timezone.utc).isoformat(),
 "status":"READ_ONLY_PROVENANCE_AUDIT",
 "expected_golden_sha256":expected,
 "golden_archive_copy_still_available":any(x.get("sha256")==expected and "golden-scene-sequence" in x["path"] for x in rows),
 "live_source_mutability":"DO_NOT_USE_LIVE_WORKSPACE_SAVE_AS_IMMUTABLE_AUTHORITY",
 "items":rows}
output=R/"runtime-test"/"results"/"openzork-save-provenance-drift-20261009-v6.json"
output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":report["status"],"expected_sha256":expected,
 "golden_archive_available":report["golden_archive_copy_still_available"],
 "files":rows,"audit":str(output)},ensure_ascii=False))
