"""Unregistered R8 source candidate. Renderer-facing entry accepts selection only."""
import hashlib
import json
import re
import sqlite3
import time
from contextlib import ExitStack, closing
from pathlib import Path

from files import hold_directory, metadata, opened, read_held, require, require_wal_header

KEYS = ("project_id", "edition_id", "committed_operation_id", "accepted_manifest_digest")
FIXED_ROOT = Path(r"C:\Users\msemj\Documents\Codex\2026-10-25\podme-rozbehat-native-worker\unified-dev-worker-06")
EMPTY_CATALOG = b"[]"
MAX_BYTES = 256 * 1024 * 1024
IDENT = r"[A-Za-z0-9_-]{1,64}"
STUDIO_SCENARIO = "build_studio_dev"
STUDIO_LAYOUT = "studio-target-debug"
STUDIO_SCHEMA = "OpenRemaster.DevBuildArtifacts.v1"
STUDIO_EXE = "openremaster_studio_shadow.exe"
PACKAGING_SCENARIO = "build_openremaster-unified_dev"
PACKAGE_EXE = "OpenRemaster-Unified-DEV-Offline-x64.exe"
PACKAGE_NAMES = {PACKAGE_EXE, "OpenRemaster-Unified-DEV-x64.msi", "build.log", "artifact-manifest.json", "README.md"}


def decode(raw):
    def unique(pairs):
        result = dict(pairs)
        require(len(result) == len(pairs), "DUPLICATE_KEY")
        return result
    return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)


def matches(value, pattern):
    return type(value) is str and bool(re.fullmatch(pattern, value, flags=re.ASCII))


def selection(value):
    require(type(value) is dict and set(value) == set(KEYS), "REQUEST_KEYS")
    for key, pattern in zip(KEYS, (IDENT, IDENT, "[0-9a-f]{32}", "[0-9a-f]{64}")):
        require(matches(value[key], pattern), "REQUEST_VALUE")
    return tuple(value[k] for k in KEYS)


def name_ok(name):
    return (matches(name, r"[A-Za-z0-9_-][A-Za-z0-9._-]{0,119}") and not name.endswith(".") and
            not re.fullmatch(r"CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]", name.partition(".")[0], re.I))


def registry(raw, pin):
    require(len(raw) <= 1 << 20 and hashlib.sha256(raw).hexdigest() == pin, "CATALOG_PIN")
    rows = decode(raw)
    require(type(rows) is list and len(rows) <= 256, "CATALOG_SIZE")
    indexed = {}
    for row in rows:
        base = {"selection","scenario","engine","source_commit","source_tree",
                "source_manifest_sha256","build_plan_sha256","input_binding_sha256","roles","expires_epoch_ms"}
        # Old non-Studio rows select only the original stage/out list. Studio
        # has never had a legacy layout and requires an explicit selection.
        require(set(row) in (base, base | {"artifact_layout", "artifact_schema"}), "CATALOG_KEYS")
        if row["scenario"] == STUDIO_SCENARIO:
            require(row.get("artifact_layout") == STUDIO_LAYOUT and row.get("artifact_schema") == STUDIO_SCHEMA
                    and row["roles"] == {"EXE": STUDIO_EXE}, "STUDIO_CATALOG_BINDING")
        elif "artifact_layout" in row:
            require(row["artifact_layout"] == "stage-out" and row["artifact_schema"] == "unversioned-files",
                    "OUT_CATALOG_BINDING")
        key = selection(row["selection"])
        require(key not in indexed and all(matches(row[k], IDENT) for k in ("engine","scenario")), "CATALOG_ID")
        for k in ("source_commit","source_tree"):
            require(matches(row[k], "[0-9a-f]{40}"), "SOURCE_ID")
        for k in ("source_manifest_sha256","build_plan_sha256","input_binding_sha256"):
            require(matches(row[k], "[0-9a-f]{64}"), "SOURCE_DIGEST")
        roles = row["roles"]
        require(type(roles) is dict and set(roles) in ({"EXE"}, {"EXE","PCK"}), "CATALOG_ROLES")
        require(all(name_ok(n) and n.lower().endswith("." + r.lower()) for r,n in roles.items()), "CATALOG_PATH")
        require(type(row["expires_epoch_ms"]) is int, "EXPIRY")
        indexed[key] = row
    return indexed


def committed(db, row, op):
    record = db.execute("SELECT scenario,state,launches,ack,result FROM operations WHERE id=?", (op,)).fetchone()
    require(record and record[:3] == (row["scenario"], "COMMITTED", 1), "NOT_COMMITTED")
    ack, result = [decode(v.encode()) for v in record[3:]]
    worker, commit = result["worker"], result["commit"]
    require(result["operation_id"] == commit["operation_id"] == op and result["scenario"] == row["scenario"]
            and result["state"] == "COMMITTED" and type(result["launch_count"]) is int and result["launch_count"] == 1
            and result["ack"] == ack, "RESULT_BINDING")
    require(worker["success"] is True and worker["owned_tree_stopped"] is True and worker["worker_state"] == "PASS"
            and commit["schema"] == "OpenRemaster.DevCommit.v1" and commit["authority"] == "LOCAL_TEST_LEDGER_ONLY"
            and hashlib.sha256(json.dumps(worker, sort_keys=True).encode()).hexdigest() == commit["worker_result_sha256"],
            "WORKER_COMMIT")
    require(worker["source_manifest_sha256"] == row["source_manifest_sha256"] and
            ack["input_binding_sha256"] == worker["input_binding_sha256"] == row["input_binding_sha256"] and
            worker["build_plan_sha256"] == commit["build_plan_sha256"] == row["build_plan_sha256"] and
            worker["artifacts_manifest_sha256"] == row["selection"]["accepted_manifest_digest"], "MANIFEST_BINDING")
    return worker


def studio_inputs(stack, stage, volume, manifest, operation, deadline, cancel):
    binary = stage / "target" / "debug" / STUDIO_EXE
    frontend = stage / "source" / "studio" / "dist" / "index.html"
    true_fields = ("frontend_build", "native_build", "native_ipc_tests")
    false_fields = ("gui_executed", "certificate_created", "installer_built", "production_go")
    require(set(manifest) == {"schema","profile","operation_id","studio_exe","studio_exe_sha256",
            "studio_exe_bytes","signature_status","frontend_index","frontend_index_sha256",
            *true_fields,*false_fields}, "STUDIO_SCHEMA_FIELDS")
    require(manifest["schema"] == STUDIO_SCHEMA and manifest["operation_id"] == operation and
            manifest["profile"] == "DEV_UNSIGNED" and manifest["signature_status"] == "NotSigned" and
            all(manifest[k] is True for k in true_fields) and all(manifest[k] is False for k in false_fields),
            "STUDIO_MANIFEST")
    # Compare the declared paths as text. Do not follow, resolve or open them.
    for key, expected in (("studio_exe",binary),("frontend_index",frontend)):
        require(type(manifest[key]) is str and manifest[key].replace("/", "\\") == str(expected)
                and matches(manifest[key+"_sha256"], "[0-9a-f]{64}"), "STUDIO_PATH_OR_HASH")
    size = manifest["studio_exe_bytes"]
    require(type(size) is int and 0 < size <= MAX_BYTES, "STUDIO_SIZE")
    for directory in (stage/"target",binary.parent, stage/"source", stage/"source/studio",frontend.parent):
        hold_directory(stack, directory, volume)
    index, _ = read_held(stack, frontend, volume, MAX_BYTES-size, deadline, cancel)
    require(index["bytes"] > 0 and index["sha256"] == manifest["frontend_index_sha256"], "FRONTEND_CHANGED")
    return binary.parent, [dict(name=STUDIO_EXE, bytes=size, sha256=manifest["studio_exe_sha256"])]


def observe_from(request, root, catalog, pin, cancel):
    def response(state, **fields):
        return dict(schema="OpenRemaster.NativeFileObservation.v1", state=state, read_only=True,
                    execution_authority=False, gameplay="UNKNOWN", fidelity="UNKNOWN",
                    observed_epoch_ms=time.time_ns() // 1000000, **fields)
    try:
        key = selection(request)
    except (ValueError, TypeError):
        return response("HOLD", reason="INVALID_REQUEST")
    try:
        row = registry(catalog, pin).get(key)
        if row is None:
            return response("HOLD", reason="NO_ACCEPTED_SELECTION")
        def fresh():
            require(time.time_ns() // 1000000 < row["expires_epoch_ms"] and
                    time.monotonic() < deadline and not cancel(), "EXPIRED")
        deadline = time.monotonic() + 2
        fresh()
        stage = root / "state" / "operations" / key[2]
        with ExitStack() as stack:
            volume = None
            for path in (*reversed(stage.parents), stage):
                volume = hold_directory(stack, path, volume)
            dbpath = root / "state" / "ledger.sqlite"
            # Pin ledger pathname while SQLite takes its own read transaction. For
            # WAL mode require an existing paired WAL/SHM; never initialize a ledger.
            ledger_handle = stack.enter_context(opened(dbpath, False, True))
            require(metadata(ledger_handle, dbpath, False)[0] == volume, "LEDGER_TYPE")
            for suffix in ("-wal", "-shm"):
                sidecar = dbpath.with_name(dbpath.name + suffix)
                handle = stack.enter_context(opened(sidecar, False, True))
                require(metadata(handle, sidecar, False)[0] == volume, "LEDGER_SIDECAR_TYPE")
            require_wal_header(ledger_handle)
            db = stack.enter_context(closing(sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True, timeout=0)))
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2 << 20)
            db.set_progress_handler(lambda: int(cancel() or time.monotonic() >= deadline), 100)
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            worker = committed(db, row, key[2])
            require(db.execute("PRAGMA journal_mode").fetchone() == ("wal",), "WAL_SNAPSHOT_REQUIRED")
            manifest_meta, raw = read_held(stack, stage / "artifacts.json", volume, 1 << 20, deadline, cancel, True)
            require(manifest_meta["sha256"] == key[3] and str(stage) == worker["stage"], "MANIFEST_CHANGED")
            manifest = decode(raw)
            require(json.dumps(manifest,sort_keys=True) == json.dumps(worker["artifacts"],sort_keys=True), "WORKER_MANIFEST")
            if row["scenario"] == STUDIO_SCENARIO:
                directory, listed = studio_inputs(stack,stage,volume,manifest,key[2],deadline,cancel)
            else:
                require("schema" not in manifest or ("artifact_schema" not in row and manifest["schema"] != STUDIO_SCHEMA),
                        "OUT_SCHEMA")
                directory, listed = stage/"out", manifest["files"]
                hold_directory(stack, directory, volume)
                if row["scenario"] == PACKAGING_SCENARIO:
                    require(set(manifest) == {"profile","signature_status","production_go","operation_id","source_snapshot","files"}
                            and manifest["operation_id"] == key[2] and manifest["source_snapshot"] == row["input_binding_sha256"]
                            and manifest["profile"] == "DEV_UNSIGNED" and manifest["signature_status"] == "NotSigned"
                            and manifest["production_go"] is False and row["roles"] == {"EXE":PACKAGE_EXE}, "PACKAGE_BINDING")
            require(type(listed) is list and 0 < len(listed) <= 64, "ARTIFACT_LIST")
            entries = {}
            for item in listed:
                name = item["name"]
                require(name_ok(name) and name.casefold() not in entries and
                        type(item["bytes"]) is int and item["bytes"] >= 0 and
                        matches(item["sha256"], "[0-9a-f]{64}"), "MANIFEST_ENTRY")
                entries[name.casefold()] = item
            roles = row["roles"]
            if row["scenario"] == PACKAGING_SCENARIO:
                require({item["name"] for item in listed} == PACKAGE_NAMES, "PACKAGE_MEMBERS")
            require({i["name"] for i in entries.values() if i["name"].lower().endswith((".exe",".pck"))}
                    == set(roles.values()), "ROLE_SET")
            files = []
            remaining = MAX_BYTES
            for role, name in roles.items():
                item = entries[name.casefold()]
                require(0 < item["bytes"] <= remaining, "AGGREGATE_LIMIT")
                meta, _ = read_held(stack, directory / name, volume, item["bytes"], deadline, cancel)
                require(meta["bytes"] == item["bytes"] and meta["sha256"] == item["sha256"], "ARTIFACT_CHANGED")
                files.append(dict(role=role, name=name, **meta))
                remaining -= meta["bytes"]
            fresh()
            return response("LIVE", selection=dict(zip(KEYS,key)), files=files, **{k:row[k] for k in
                            ("engine","source_commit","source_tree","source_manifest_sha256","build_plan_sha256")})
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, sqlite3.Error):
        return response("HOLD", reason="UNVERIFIED")


def observe(request):
    return observe_from(request, FIXED_ROOT, EMPTY_CATALOG, hashlib.sha256(b"[]").hexdigest(), lambda: False)
