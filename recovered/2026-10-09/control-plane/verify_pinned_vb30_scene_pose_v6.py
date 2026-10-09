"""Independent re-verification of the pinned, not shared, OpenZork Golden Scene save.
Retains old divergent live file as evidence; does not rewrite or clean it.
"""
from pathlib import Path
import json,hashlib,struct,stat,re
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[2]
pin_dir=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"
pin=pin_dir/"znemesis.000"
manifest=pin_dir/"pinned-save-manifest.json"
drift=R/"runtime-test"/"results"/"openzork-save-provenance-drift-20261009-v6.json"
original_pose=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"/"vb30-save-scene-pose-and-decoder-v6.json"
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads(manifest.read_text(encoding="utf-8-sig"))
r=json.loads(drift.read_text(encoding="utf-8-sig"))
pose=json.loads(original_pose.read_text(encoding="utf-8-sig"))
assert m["schema"]=="OpenZork.PinnedSavedStateOracle.v1" and m["status"]=="PINNED_GOLDEN_SCENE_SAVE_HASH_VERIFIED"
b=pin.read_bytes()
assert len(b)==120044 and h(pin)==m["pinned_sha256"]
assert b[:4]==b"ZNSG"
version=struct.unpack_from("<I",b,4)[0]
assert version==4
assert b[12:16]==b"LOC " and struct.unpack_from("<I",b,16)[0]==8
scene=b[20:24].decode("ascii")
view=struct.unpack_from("<I",b,24)[0]
assert scene=="vb30" and view==1058
assert pose["save_sha256"]==h(pin) and pose["location_key"]==scene.upper() and pose["view_coordinate"]==view
assert not pin.stat().st_mode&stat.S_IWRITE
old_staging=Path(pose["save_path"])
current_hash=h(old_staging) if old_staging.is_file() else None
if current_hash is not None and current_hash!=h(pin):
 live_status="DRIFTED_DO_NOT_USE"
else:
 live_status="HASH_EQUAL_AT_CHECK_ONLY_NOT_AUTHORITY"
proof={
 "schema":"OpenZork.VB30PinnedSavePoseProvenance.v1",
 "status":"PINNED_SAVE_REVERIFIED_VB30_1058",
 "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
 "scene":"VB30","view":1058,"format":"ZNSG","version":4,
 "sha256":h(pin),"bytes":len(b),
 "pinned_save":str(pin),"pinned_manifest_sha256":h(manifest),
 "NTFS_readonly_attribute_verified":True,
 "previous_private_capture_save_sha256":m["original_sha256"],
 "previous_pose_evidence_sha256":h(original_pose),
 "live_work_staging_save_status":live_status,
 "live_work_staging_save_sha256_at_check":current_hash,
 "live_source_is_authority":False,
 "historical_live_staging_file_modified_by_this_verification":False,
 "fidelity_reconstruction_validated":False
}
dest=pin_dir/"pinned-pose-reverification.json"
if dest.exists():raise RuntimeError("PERSISTENT_POSE_REVERIFICATION_ALREADY_EXISTS")
dest.write_text(json.dumps(proof,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":proof["status"],"scene":"VB30@1058",
 "sealed_sha256":proof["sha256"],"read_only":True,
 "mutable_old_staging":live_status,
 "evidence":str(dest)},ensure_ascii=False))
