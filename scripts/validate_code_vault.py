"""Read-only integrity check for the pinned OpenRemaster remote code vault.

Only Git object metadata is inspected; no recovered source is executed.
This verifies Git blob identities/sizes, not external source SHA-256 claims.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

VAULT_SNAPSHOT = "c7bba9c377e8b2193797e7f7252c0aaf354baad1"
REPO_NAME = "semishsvk/OpenRemaster-Framework"
METADATA = frozenset({"CODE_VAULT_MANIFEST.json", "CODE_VAULT_README.md"})
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


class VaultIntegrityError(ValueError):
    """A mismatch or missing piece of authority must fail closed."""


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise VaultIntegrityError(f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def parse_ls_tree(payload: bytes) -> dict[str, tuple[str, int, str]]:
    """Decode git ls-tree -rz -l without text-line path ambiguity."""
    entries: dict[str, tuple[str, int, str]] = {}
    for item in payload.split(b"\0"):
        if not item:
            continue
        try:
            metadata, name = item.split(b"\t", 1)
            mode, kind, sha, size = metadata.decode("ascii").split()
            path = name.decode("utf-8", "strict")
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise VaultIntegrityError(f"unsupported Git object or mode: {path}")
            if not GIT_SHA.fullmatch(sha) or not size.isdecimal():
                raise VaultIntegrityError(f"invalid Git metadata: {path}")
            if path in entries or not path or path.startswith("/") or ".." in path.split("/"):
                raise VaultIntegrityError(f"unsafe or duplicate path: {path!r}")
        except (UnicodeError, ValueError) as exc:
            if isinstance(exc, VaultIntegrityError):
                raise
            raise VaultIntegrityError("invalid git ls-tree record") from exc
        entries[path] = (sha, int(size), mode)
    return entries


def validate_manifest(
    manifest: dict, snapshot_entries: dict[str, tuple[str, int, str]]
) -> tuple[int, int]:
    if manifest.get("schema") != "openremaster.remote-code-vault.v1":
        raise VaultIntegrityError("unsupported vault schema")
    if manifest.get("repository") != REPO_NAME:
        raise VaultIntegrityError("unexpected repository")
    if manifest.get("status") != "ARCHIVED_UNVALIDATED_DO_NOT_DEPLOY":
        raise VaultIntegrityError("vault is not marked quarantined")

    src = manifest.get("immutable_sources")
    if not isinstance(src, dict) or not isinstance(manifest.get("inventory"), list):
        raise VaultIntegrityError("missing source or inventory data")
    main, m001, recovery = (src.get(k, {}) for k in (
        "canonical_main", "m001_remote_control", "recovery_code_snapshot"))
    if (
        main.get("commit") != "8195f3754219b487deb0947a29d8af6cfe1babc9"
        or m001.get("commit") != "ec415f36e86a74cf7e3d651569a437eea0a25585"
        or recovery.get("commit") != "4326d2c184b6865743bb20f8c89e745bd110fd09"
        or recovery.get("recovered_subtree_sha") != "67ea3de8f662547d08d708c278a11b3c34f30d54"
    ):
        raise VaultIntegrityError("pinned authority changed")

    inventory = manifest["inventory"]
    listed: set[str] = set()
    recovered = 0
    for entry in inventory:
        if not isinstance(entry, dict):
            raise VaultIntegrityError("malformed inventory row")
        path, sha, size = (entry.get(field) for field in ("path", "git_blob_sha", "size_bytes"))
        if not isinstance(path, str) or path in listed or path in METADATA:
            raise VaultIntegrityError(f"duplicate or forbidden manifest entry: {path!r}")
        if not isinstance(sha, str) or not GIT_SHA.fullmatch(sha):
            raise VaultIntegrityError(f"invalid Git blob identity: {path}")
        if type(size) is not int or size < 0:
            raise VaultIntegrityError(f"invalid Git file size: {path}")
        got = snapshot_entries.get(path)
        if got is None or got[:2] != (sha, size):
            raise VaultIntegrityError(f"missing/changed snapshot blob: {path}")
        if got[2] != "100644":
            raise VaultIntegrityError(f"unexpected executable bit: {path}")
        is_recovered = path.startswith("recovered/2026-10-09/")
        if is_recovered:
            recovered += 1
            if entry.get("source") not in {"recovery-snapshot", "recovery-metadata"}:
                raise VaultIntegrityError(f"invalid recovery classification: {path}")
        elif entry.get("source") != "m001":
            raise VaultIntegrityError(f"invalid canonical classification: {path}")
        listed.add(path)

    if set(snapshot_entries) != listed | METADATA:
        raise VaultIntegrityError("unexpected/missing files in pinned Git snapshot")
    if len(inventory) != 522 or recovered != 379:
        raise VaultIntegrityError("unexpected inventory counts")
    return len(inventory), recovered


def verify_repository(repo: Path) -> tuple[int, int]:
    manifest = json.loads((repo / "CODE_VAULT_MANIFEST.json").read_text(encoding="utf-8"))
    parent_line = git(repo, "rev-list", "--parents", "-n", "1", VAULT_SNAPSHOT).decode().strip().split()
    expected_parents = [VAULT_SNAPSHOT,
                        manifest["immutable_sources"]["m001_remote_control"]["commit"],
                        manifest["immutable_sources"]["recovery_code_snapshot"]["commit"]]
    if parent_line != expected_parents:
        raise VaultIntegrityError("vault parent commits differ from manifest")
    snapshot_entries = parse_ls_tree(git(repo, "ls-tree", "-r", "-z", "-l", VAULT_SNAPSHOT))
    counts = validate_manifest(manifest, snapshot_entries)
    recovered_sha = git(repo, "rev-parse", "HEAD:recovered").decode().strip()
    if recovered_sha != manifest["immutable_sources"]["recovery_code_snapshot"]["recovered_subtree_sha"]:
        raise VaultIntegrityError("quarantined recovered source tree has changed")
    return counts


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    try:
        included, recovered = verify_repository(repo)
    except (VaultIntegrityError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"CODE_VAULT_INTEGRITY: FAIL — {exc}", file=sys.stderr)
        return 1
    print(f"CODE_VAULT_INTEGRITY: PASS — {included} pinned entries, {recovered} recovered files")
    print("Status remains ARCHIVED_UNVALIDATED_DO_NOT_DEPLOY; no source-byte or runtime fidelity claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
