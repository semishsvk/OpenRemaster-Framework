"""Exact project/source/runtime executable and private config binding.
Prevents wrong-game DOSBox or ScummVM from being reported under a different project.
The registry contains only verified targets; unknown games must be commissioned.
"""
from pathlib import Path
import configparser
import json,re,hashlib
from fidelity_runtime_isolation_v1 import IsolationError,sha256

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=Path(__file__).with_name("fidelity-runtime-target-registry.v7.json")

def registry():
    value=json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    if value.get("schema")!="OpenRemaster.VerifiedInteractiveRuntimeTargets.v1":
        raise IsolationError("RUNTIME_TARGET_REGISTRY_SCHEMA_INVALID")
    return value

def validate_registered_target(project,kind,exe):
    """Fail closed on unknown project/runtime mapping or changed EXE bytes."""
    record=registry()
    candidates=[x for x in record["entries"]
                if x.get("project")==project and x.get("runtime_kind")==kind]
    if not candidates:
        raise IsolationError("RUNTIME_PROJECT_KIND_NOT_COMMISSIONED",
                             {"project":project,"kind":kind})
    executable=Path(exe).resolve()
    exact=[item for item in candidates if Path(item["executable"]).resolve()==executable]
    if len(exact)!=1:
        raise IsolationError("RUNTIME_EXECUTABLE_NOT_REGISTERED_FOR_PROJECT",
                             {"project":project,"kind":kind,
                              "executable":str(executable)})
    item=exact[0]
    digest=sha256(executable)
    if digest!=item["executable_sha256"]:
        raise IsolationError("RUNTIME_EXECUTABLE_HASH_CHANGED",
                             {"expected":item["executable_sha256"],"actual":digest})
    if item.get("classification")=="SYNTHETIC_WIN32_CANARY_ONLY" and project!="OpenRemaster":
        raise IsolationError("SYNTHETIC_CANARY_PROJECT_MISMATCH")
    return item

def validate_game_config_binding(item,config_path):
    """Read *private copied* config; never touch source config or game files."""
    kind=item["runtime_kind"]
    classification=item["classification"]
    if classification=="SYNTHETIC_WIN32_CANARY_ONLY":
        if item["project"]!="OpenRemaster":
            raise IsolationError("SYNTHETIC_RUNTIME_GAME_CLAIM_FORBIDDEN")
        return {"status":"PASS_SYNTHETIC_NO_GAME_AUTHORITY",
                "registered_runtime":item["executable_sha256"]}
    expected=item.get("source_root")
    if not expected:
        raise IsolationError("CANONICAL_SOURCE_ROOT_NOT_REGISTERED")
    canon=Path(expected).resolve()
    if not canon.is_dir():
        raise IsolationError("CANONICAL_SOURCE_ROOT_UNAVAILABLE")
    config=Path(config_path)
    if not config.is_file():
        raise IsolationError("PRIVATE_CONFIG_MISSING")
    text=config.read_text(encoding="utf-8-sig",errors="replace")
    if kind=="scummvm":
        c=configparser.ConfigParser(interpolation=None)
        try:
            c.read_string(text)
        except configparser.Error as e:
            raise IsolationError("SCUMMVM_PRIVATE_INI_UNPARSEABLE",
                                 {"exception":type(e).__name__})
        if not c.has_section("znemesis") or not c.has_option("znemesis","path"):
            raise IsolationError("SCUMMVM_TARGET_GAME_MISSING")
        gamepath=Path(c.get("znemesis","path")).resolve()
        if gamepath!=canon:
            raise IsolationError("SCUMMVM_TARGET_PATH_DIFFERENT_GAME",
                                 {"actual":str(gamepath),"expected":str(canon)})
        if c.get("znemesis","gameid",fallback="").lower()!="zvision":
            raise IsolationError("SCUMMVM_TARGET_ENGINE_DIFFERENT")
        return {"status":"PASS_SOURCE_BOUND","project":item["project"],
                "config_game_root":str(canon),"game_engine":"zvision",
                "registered_runtime_sha256":item["executable_sha256"]}
    if kind=="dosbox":
        valid=[]
        foreign=[]
        for raw in text.splitlines():
            line=raw.strip()
            if not line or line.startswith(("#",";")):
                continue
            if not re.match(r"(?i)^mount\s+[a-z]\s+",line):
                continue
            # Original source directories must be explicitly read only.
            match=re.match(r'(?i)^mount\s+[a-z]\s+"([^"]+)"(.*)$',line)
            if not match:
                raise IsolationError("DOSBOX_GAME_MOUNT_UNPARSEABLE",
                                     {"line":line[:160]})
            path=Path(match.group(1)).resolve()
            rest=match.group(2)
            if path==canon:
                if not re.search(r"(?i)(?:^|\s)-ro(?:\s|$)",rest):
                    raise IsolationError("DOSBOX_SOURCE_MOUNT_NOT_READ_ONLY")
                valid.append(str(path))
            else:
                if path==(ROOT/"source").resolve() or (ROOT/"source").resolve() in path.parents:
                    foreign.append(str(path))
        if foreign:
            raise IsolationError("DOSBOX_FOREIGN_SOURCE_MOUNT",
                                 {"mounts":foreign})
        if not valid:
            raise IsolationError("DOSBOX_EXPECTED_ORIGINAL_GAME_NOT_MOUNTED",
                                 {"expected":str(canon)})
        return {"status":"PASS_SOURCE_BOUND","project":item["project"],
                "config_game_root":str(canon),
                "game_engine":"original_DOS_ZORKDOS",
                "registered_runtime_sha256":item["executable_sha256"],
                "read_only_original_mount_count":len(valid)}
    raise IsolationError("RUNTIME_GAME_CONFIG_BINDING_NOT_COMMISSIONED")
