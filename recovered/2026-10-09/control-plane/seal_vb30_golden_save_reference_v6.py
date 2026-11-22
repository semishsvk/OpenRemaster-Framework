"""Create a new hash-pinned seed oracle from the *verified private run copy*.
Never copy from concurrently writable legacy staging save. New evidence only.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,os,stat,struct
R=Path(__file__).resolve().parents[2]
old=R/"runtime-test"/"results"/"openzork-scummvm-golden-scene-sequence-0e2fdd87"/"fidelity-isolated"/"saves"/"znemesis.000"
expected="3742d4e4be25561bea21ee1e63aed9029bef409f9cb56b323f8dd5ef254da5dc"
h=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert old.is_file() and h(old)==expected,"GOLDEN_PRIVATE_SEED_CHANGED"
raw=old.read_bytes()
assert len(raw)==120044 and raw[:4]==b"ZNSG" and raw[12:16]==b"LOC "
assert struct.unpack_from("<I",raw,16)[0]==8
assert raw[20:24]==b"vb30" and struct.unpack_from("<I",raw,24)[0]==1058
dir=R/"output"/"projects"/"OpenZork"/"evidence"/"20261009-VB30-SEED-PINNED-v1"
if dir.exists():raise RuntimeError("PINNED_EVIDENCE_ALREADY_EXISTS_NO_OVERWRITE")
dir.mkdir(parents=True,exist_ok=False)
file=dir/"znemesis.000"
shutil.copyfile(old,file)
assert h(file)==expected
# The Windows read-only file attribute is additional accidental-write protection;
# SHA-256, no-overwrite output location and re-verification remain the authority.
os.chmod(file,stat.S_IREAD)
read_only=(not os.access(file,os.W_OK))  # On Windows may report differently for a token.
check=h(file)
assert check==expected
record={
 "schema":"OpenZork.PinnedSavedStateOracle.v1",
 "status":"PINNED_GOLDEN_SCENE_SAVE_HASH_VERIFIED",
 "created_utc":datetime.now(timezone.utc).isoformat(),
 "canonical_game_source":"ORIGINAL_ZORK_NEMESIS_READ_ONLY",
 "historical_input_source":"WORK_STAGING_SAVE_DRIFT_DETECTED_DO_NOT_REUSE",
 "source_private_run":str(old),
 "pinned_save_path":str(file),
 "original_sha256":expected,
 "pinned_sha256":check,
 "byte_count":len(raw),
 "save_format":"ScummVM ZNSG v4",
 "location_scene":"VB30","view_position":1058,
 "NTFS_readonly_attribute_requested":True,
 "read_only_mode":oct(file.stat().st_mode),
 "os_access_W_OK_result":bool(os.access(file,os.W_OK)),
 "hash_is_authority":True,
 "no_original_source_or_old_save_file_modified":True
}
manifest=dir/"pinned-save-manifest.json"
manifest.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding="utf-8")
print(json.dumps({"status":record["status"],"sha256":check,"file":str(file),
 "save_location":"VB30@1058","bytes":len(raw),
 "read_only_attribute_requested":True,
 "evidence":str(manifest)},ensure_ascii=False))
