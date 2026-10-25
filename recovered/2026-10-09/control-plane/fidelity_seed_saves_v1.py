"""Read-only hash-bound game save seeds into a unique private supervised runtime dir.
First supported game: OpenZork/ScummVM Zork Nemesis. No original source mutation.
"""
import hashlib,json,re,shutil,struct,stat
from pathlib import Path
from fidelity_runtime_isolation_v1 import IsolationError,sha256

ROOT=Path(__file__).resolve().parents[2]

def stage_seed_saves(saves_dir,project,items):
    if not isinstance(items,list) or not 1<=len(items)<=4:
        raise IsolationError("SAVE_SEED_SPEC_INVALID")
    if project!="OpenZork":
        raise IsolationError("GAME_SEED_ADAPTER_NOT_COMMISSIONED",{"project":project})
    dst=Path(saves_dir).resolve()
    allow=(ROOT/"work"/project).resolve()
    allow_pinned=(ROOT/"output"/"projects"/project/"evidence").resolve()
    if not dst.is_dir() or (ROOT/"source").resolve() in dst.parents:
        raise IsolationError("SAVE_SEED_DESTINATION_INVALID")
    entries=[]
    seen=set()
    for i,entry in enumerate(items,1):
        if not isinstance(entry,dict) or set(entry)!={"path","sha256"}:
            raise IsolationError("SAVE_SEED_RECORD_INVALID",{"index":i})
        path=Path(entry["path"]).resolve(strict=True)
        pinned=allow_pinned in path.parents
        working_source=allow in path.parents
        if not (pinned or working_source) or not path.is_file():
            raise IsolationError("SAVE_SEED_SOURCE_OUTSIDE_PROJECT",{"index":i})
        if not re.fullmatch(r"(?i)znemesis\.[0-9]{3}",path.name):
            raise IsolationError("SAVE_SEED_FILENAME_NOT_ALLOWLISTED",{"name":path.name})
        if path.name.lower() in seen:
            raise IsolationError("SAVE_SEED_DUPLICATE_NAME")
        seen.add(path.name.lower())
        size=path.stat().st_size
        if not 32<=size<=8*1024*1024:
            raise IsolationError("SAVE_SEED_FILE_SIZE_UNSAFE",{"bytes":size})
        digest=sha256(path)
        if digest.lower()!=entry["sha256"].lower():
            raise IsolationError("SAVE_SEED_HASH_MISMATCH",{"file":str(path)})
        raw=path.read_bytes()
        if len(raw)<28 or raw[:4]!=b"ZNSG":
            raise IsolationError("SAVE_SEED_MAGIC_INVALID",{"file":str(path)})
        version=struct.unpack_from("<I",raw,4)[0]
        if version!=4 or raw[12:16]!=b"LOC " or struct.unpack_from("<I",raw,16)[0]!=8:
            raise IsolationError("SAVE_SEED_VERSION_OR_LOC_INVALID",{"version":version})
        try:scene=raw[20:24].decode("ascii")
        except UnicodeDecodeError:raise IsolationError("SAVE_SEED_SCENE_INVALID")
        view=struct.unpack_from("<I",raw,24)[0]
        if not re.fullmatch(r"[a-z]{2}[0-9]{2}",scene) or not 0<=view<1440:
            raise IsolationError("SAVE_SEED_SCENE_OR_VIEW_INVALID",{"scene":scene,"view":view})
        if pinned:
            record=path.parent/"pinned-save-manifest.json"
            if not record.is_file():
                raise IsolationError("SAVE_SEED_PINNED_MANIFEST_MISSING")
            info=json.loads(record.read_text(encoding="utf-8-sig"))
            if (info.get("schema")!="OpenZork.PinnedSavedStateOracle.v1"
                    or info.get("status")!="PINNED_GOLDEN_SCENE_SAVE_HASH_VERIFIED"
                    or Path(info.get("pinned_save_path","")).resolve()!=path
                    or info.get("pinned_sha256")!=digest):
                raise IsolationError("SAVE_SEED_PINNED_MANIFEST_MISMATCH")
            if path.stat().st_mode & stat.S_IWRITE:
                raise IsolationError("SAVE_SEED_PINNED_FILE_WRITABLE")
        target=dst/path.name
        if target.exists():
            raise IsolationError("SAVE_SEED_TARGET_ALREADY_EXISTS")
        shutil.copyfile(path,target)
        if sha256(target)!=digest:
            target.unlink(missing_ok=True)
            raise IsolationError("SAVE_SEED_COPY_HASH_MISMATCH")
        entries.append({"schema":"OpenRemaster.GameSeedCopyRecord.v1",
            "original_path":str(path),"original_sha256":digest,
            "original_size":size,"private_copy_path":str(target),
            "private_copy_sha256":sha256(target),"game":"OpenZork",
            "original_read_only":True,
            "source_kind":"PINNED_EVIDENCE" if pinned else "HASH_GUARDED_LIVE_WORK",
            "seed_scene":scene,"seed_view":view,
            "pinned_source_manifest":str(path.parent/"pinned-save-manifest.json") if pinned else None})
    return {"schema":"OpenRemaster.GameSeedMaterialization.v1",
            "status":"PASS_SOURCE_READ_ONLY",
            "project":project,"entries":entries,
            "unique_private_output_directory":str(dst)}
