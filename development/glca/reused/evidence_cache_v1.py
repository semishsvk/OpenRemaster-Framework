"""Disposable, source-bound graph projection. Never an owner or evidence authority.

SQLite provides single-host atomic cache updates. Callers retain an expected
head and revalidate source pins; neither this DB nor SHA supplies antirollback
authority, production admission, cross-host fencing or automatic retry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import closing
import hashlib
import heapq
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

from vendor.evidence_behavior import EvidenceGraph, EvidenceNode

SCHEMA = "OpenRemaster.DerivedEvidenceSnapshot.v1"
SQL = "CREATE TABLE snapshots (seq INTEGER PRIMARY KEY, previous TEXT NOT NULL, token TEXT NOT NULL, payload BLOB NOT NULL)"
ZERO = "0" * 64
MAX_NODES, MAX_REVISIONS, MAX_PAYLOAD, MAX_DB = 512, 128, 1024 * 1024, 32 * 1024 * 1024
SHA = re.compile(r"^[0-9a-f]{64}$")
IDENT = re.compile(r"^[A-Za-z0-9_.:/-]{1,160}$")


class CacheHold(ValueError):
    """An explicit review/rebuild is needed; never retry automatically."""


def require(ok, reason):
    if not ok:
        raise CacheHold(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sha(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def strict_json(blob):
    require(type(blob) is bytes and len(blob) <= MAX_PAYLOAD, "PAYLOAD_SIZE_OR_TYPE")
    try:
        return json.loads(blob, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(CacheHold("NONFINITE_JSON")))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise CacheHold("INVALID_JSON") from exc


def snapshot(nodes, source_basis_sha256, external_validation=None):
    """Canonicalize immutable values, including edges and validation references."""
    require(type(nodes) in (list, tuple) and len(nodes) <= MAX_NODES, "NODE_LIMIT_OR_TYPE")
    require(sha(source_basis_sha256), "SOURCE_BASIS_REQUIRED")
    rows = []
    for node in nodes:
        require(type(node) is EvidenceNode, "NODE_TYPE")
        for value in (node.key, node.project, node.kind):
            require(type(value) is str and IDENT.fullmatch(value), "NODE_IDENTITY")
        require(sha(node.digest), "NODE_DIGEST")
        require(type(node.parents) is tuple and len(node.parents) <= MAX_NODES,
                "PARENTS_TYPE_OR_LIMIT")
        require(all(type(p) is str and IDENT.fullmatch(p) for p in node.parents), "PARENT_IDENTITY")
        require(node.independent_validation == "" or sha(node.independent_validation), "VALIDATION_REFERENCE")
        row = asdict(node)
        row["parents"] = sorted(node.parents)
        rows.append(row)
    try:
        EvidenceGraph(list(nodes), external_validation=external_validation)
    except (ValueError, RecursionError) as exc:
        raise CacheHold(str(exc)) from exc
    result = {"schema": SCHEMA, "source_basis_sha256": source_basis_sha256,
              "nodes": sorted(rows, key=lambda r: r["key"])}
    require(len(canonical(result)) <= MAX_PAYLOAD, "SNAPSHOT_TOO_LARGE")
    return result


def validate(value, external_validation=None):
    require(type(value) is dict and set(value) == {"schema", "source_basis_sha256", "nodes"}
            and value["schema"] == SCHEMA, "SNAPSHOT_SCHEMA")
    require(type(value["nodes"]) is list and len(value["nodes"]) <= MAX_NODES, "NODE_LIMIT_OR_TYPE")
    nodes = []
    for row in value["nodes"]:
        require(type(row) is dict and set(row) == {
            "key", "project", "digest", "kind", "parents", "independent_validation"}, "NODE_FIELDS")
        require(type(row["parents"]) is list, "PARENTS_TYPE_OR_LIMIT")
        nodes.append(EvidenceNode(**{**row, "parents": tuple(row["parents"])}))
    normalized = snapshot(nodes, value["source_basis_sha256"], external_validation)
    require(value == normalized, "NONCANONICAL_SNAPSHOT")
    return normalized


def impact(previous, current, external_validation=None):
    """Invalidate old OR new descendants, including removed edges and nodes.

    Order recomputation by the new DAG, not the union (which may have a cycle
    when an edge reverses). Removed claims are explicitly retired.
    """
    old = validate(previous, external_validation)
    new = validate(current, external_validation)
    a, b = ({n["key"]: n for n in s["nodes"]} for s in (old, new))
    added, removed = set(b) - set(a), set(a) - set(b)
    modified = {k for k in set(a) & set(b) if a[k] != b[k]}
    changed = added | removed | modified
    children = {}
    for rows in (a, b):
        for key, row in rows.items():
            for parent in row["parents"]:
                children.setdefault(parent, set()).add(key)
    affected, todo = set(changed), list(changed)
    while todo:
        for child in children.get(todo.pop(), ()):
            if child not in affected:
                affected.add(child)
                todo.append(child)
    rebuild = affected & set(b)
    indegrees = {k: sum(p in rebuild for p in b[k]["parents"]) for k in rebuild}
    new_children = {}
    for key in rebuild:
        for parent in b[key]["parents"]:
            new_children.setdefault(parent, []).append(key)
    ready = [k for k in rebuild if indegrees[k] == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        key = heapq.heappop(ready)
        order.append(key)
        for child in new_children.get(key, ()):
            indegrees[child] -= 1
            if indegrees[child] == 0:
                heapq.heappush(ready, child)
    require(len(order) == len(rebuild), "REBUILD_CYCLE")
    basis_changed = old["source_basis_sha256"] != new["source_basis_sha256"]
    return {"status": "REVERIFY_REQUIRED" if changed or basis_changed else "NO_CHANGE",
            "added": sorted(added), "removed": sorted(removed), "modified": sorted(modified),
            "invalidate": sorted(affected - changed), "rebuild_order": order,
            "retire": sorted(removed), "source_basis_changed": basis_changed,
            "source_revalidation_required": basis_changed,
            "may_dispatch": False, "may_promote_fidelity": False, "may_auto_retry": False}


@dataclass(frozen=True)
class Head:
    sequence: int
    token: str


def _safe_path(path, arena):
    path, arena = Path(path).absolute(), Path(arena).absolute()
    require(path.parent == arena and arena.is_dir(), "CACHE_OUTSIDE_EXPLICIT_ARENA")
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            require(component == path, "ARENA_MISSING")
            continue
        require(not stat.S_ISLNK(info.st_mode) and
                not (getattr(info, "st_file_attributes", 0) & 0x400), "REPARSE_PATH")
    if path.exists():
        info = path.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_DB,
                "CACHE_FILE_TYPE_OR_SIZE")
    return path


class SnapshotCache:
    """Append immutable cache generations with local compare-and-swap.

    Trust boundary: caller-owned isolated directory, no hostile filesystem
    replacement. Path checks are preflight, not kernel handle-relative defense.
    A failed/interrupted create remains for inspection; it is never healed.
    """
    def __init__(self, path, *, arena, external_validation=None):
        self.path = _safe_path(path, arena)
        self.arena = Path(arena).absolute()
        self.external_validation = external_validation

    def create(self):
        _safe_path(self.path, self.arena)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError as exc:
            raise CacheHold("CACHE_ALREADY_EXISTS") from exc
        with closing(self._connect(False)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(SQL)
            conn.execute("PRAGMA user_version=1")
            conn.commit()

    def _connect(self, readonly):
        _safe_path(self.path, self.arena)
        require(self.path.exists(), "CACHE_MISSING")
        conn = None
        try:
            conn = sqlite3.connect(self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"),
                                   uri=True, timeout=0.2, isolation_level=None)
            conn.execute("PRAGMA trusted_schema=OFF")
            conn.execute("PRAGMA foreign_keys=ON")
            if readonly:
                conn.execute("PRAGMA query_only=ON")
            else:
                conn.execute("PRAGMA synchronous=FULL")
            return conn
        except sqlite3.Error as exc:
            if conn is not None:
                conn.close()
            raise CacheHold("CACHE_OPEN_OR_BUSY") from exc

    def _read(self, conn):
        require(conn.execute("PRAGMA user_version").fetchone() == (1,), "CACHE_VERSION")
        require(conn.execute("SELECT type,name,sql FROM sqlite_master ORDER BY name").fetchall()
                == [("table", "snapshots", SQL)], "CACHE_SCHEMA")
        rows = conn.execute("SELECT seq,previous,token,payload FROM snapshots ORDER BY seq LIMIT ?",
                            (MAX_REVISIONS + 1,)).fetchall()
        require(len(rows) <= MAX_REVISIONS, "CACHE_HISTORY_LIMIT")
        last, latest = ZERO, None
        for index, (seq, previous, token, blob) in enumerate(rows, 1):
            require(type(seq) is int and seq == index and previous == last and sha(token), "CACHE_CHAIN")
            value = validate(strict_json(blob), self.external_validation)
            require(canonical(value) == blob, "CACHE_ENCODING")
            require(token == digest({"sequence": seq, "previous": previous, "snapshot": value}), "CACHE_DIGEST")
            last, latest = token, value
        return (Head(len(rows), last) if rows else None), latest

    def load(self, *, expected_head=None, expected_source_basis=None):
        conn = self._connect(True)
        try:
            conn.execute("BEGIN")
            head, value = self._read(conn)
            if expected_head is not None:
                require(type(expected_head) is Head and head == expected_head, "HEAD_CHANGED_OR_ROLLBACK")
            if expected_source_basis is not None:
                require(sha(expected_source_basis) and value is not None and
                        value["source_basis_sha256"] == expected_source_basis, "SOURCE_BASIS_STALE")
            return head, value
        except sqlite3.Error as exc:
            raise CacheHold("CACHE_READ_OR_BUSY") from exc
        finally:
            conn.close()

    def commit(self, value, *, expected_head):
        value = validate(value, self.external_validation)
        require(expected_head is None or type(expected_head) is Head, "EXPECTED_HEAD_TYPE")
        conn = self._connect(False)
        try:
            conn.execute("BEGIN IMMEDIATE")
            head, previous_value = self._read(conn)
            require(head == expected_head, "CAS_CONFLICT")
            if previous_value == value:
                conn.rollback()
                return head
            sequence = head.sequence + 1 if head else 1
            require(sequence <= MAX_REVISIONS, "CACHE_HISTORY_LIMIT")
            previous = head.token if head else ZERO
            token = digest({"sequence": sequence, "previous": previous, "snapshot": value})
            conn.execute("INSERT INTO snapshots VALUES (?,?,?,?)",
                         (sequence, previous, token, canonical(value)))
            conn.commit()
            return Head(sequence, token)
        except sqlite3.Error as exc:
            raise CacheHold("CACHE_WRITE_OR_BUSY") from exc
        finally:
            conn.close()
