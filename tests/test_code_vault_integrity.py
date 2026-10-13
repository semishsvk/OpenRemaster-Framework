"""Pure tests of the vault inventory verifier. No recovered modules executed."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_code_vault.py"
spec = importlib.util.spec_from_file_location("validate_code_vault", SCRIPT)
vault = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vault)


def fixture():
    entries = {
        "src/test.py": ("a" * 40, 17, "100644"),
        "recovered/2026-10-09/tool.py": ("b" * 40, 19, "100644"),
        "CODE_VAULT_MANIFEST.json": ("c" * 40, 300, "100644"),
        "CODE_VAULT_README.md": ("d" * 40, 300, "100644"),
    }
    manifest = {
        "schema": "openremaster.remote-code-vault.v1",
        "repository": "semishsvk/OpenRemaster-Framework",
        "status": "ARCHIVED_UNVALIDATED_DO_NOT_DEPLOY",
        "immutable_sources": {
            "canonical_main": {"commit": "8195f3754219b487deb0947a29d8af6cfe1babc9"},
            "m001_remote_control": {"commit": "ec415f36e86a74cf7e3d651569a437eea0a25585"},
            "recovery_code_snapshot": {
                "commit": "4326d2c184b6865743bb20f8c89e745bd110fd09",
                "recovered_subtree_sha": "67ea3de8f662547d08d708c278a11b3c34f30d54",
            },
        },
        "inventory": [
            {"path": "src/test.py", "git_blob_sha": "a" * 40, "size_bytes": 17, "source": "m001"},
            {"path": "recovered/2026-10-09/tool.py", "git_blob_sha": "b" * 40, "size_bytes": 19, "source": "recovery-snapshot"},
        ],
    }
    return manifest, entries


def test_ls_tree_binary_safe():
    payload = b"100644 blob " + b"a" * 40 + b" 17\tsrc/test.py\0"
    assert vault.parse_ls_tree(payload) == {"src/test.py": ("a" * 40, 17, "100644")}


@pytest.mark.parametrize("payload", [
    b"120000 blob " + b"a" * 40 + b" 2\tsrc/link\0",
    b"100644 blob " + b"a" * 40 + b" 2\t../escape\0",
    b"bad record\0",
])
def test_reject_invalid_ls_tree(payload):
    with pytest.raises(vault.VaultIntegrityError):
        vault.parse_ls_tree(payload)


@pytest.mark.parametrize("tamper", ["hash", "size", "executable", "missing", "extra", "duplicate", "classification", "status", "authority"])
def test_manifest_mismatch_fail_closed(tamper):
    m, files = fixture()
    m, files = copy.deepcopy(m), copy.deepcopy(files)
    if tamper == "hash":
        m["inventory"][0]["git_blob_sha"] = "9" * 40
    elif tamper == "size":
        m["inventory"][1]["size_bytes"] = 30
    elif tamper == "executable":
        files["src/test.py"] = ("a" * 40, 17, "100755")
    elif tamper == "missing":
        del files["src/test.py"]
    elif tamper == "extra":
        files["src/unlisted.py"] = ("e" * 40, 10, "100644")
    elif tamper == "duplicate":
        m["inventory"].append(copy.deepcopy(m["inventory"][0]))
    elif tamper == "classification":
        m["inventory"][1]["source"] = "m001"
    elif tamper == "status":
        m["status"] = "PRODUCTION_READY"
    elif tamper == "authority":
        m["immutable_sources"]["canonical_main"]["commit"] = "0" * 40
    with pytest.raises(vault.VaultIntegrityError):
        vault.validate_manifest(m, files)


def test_full_manifest_uses_exact_count_gate():
    m, files = fixture()
    with pytest.raises(vault.VaultIntegrityError, match="unexpected inventory counts"):
        vault.validate_manifest(m, files)


def test_synthetic_complete_inventory_passes():
    manifest, files = fixture()
    # Construct a synthetic inventory of the same size/classification as the
    # real frozen snapshot without reading or executing recovered source code.
    for i in range(378):
        path = f"recovered/2026-10-09/extra-{i:03d}.py"
        files[path] = ("e" * 40, i, "100644")
        manifest["inventory"].append({
            "path": path, "git_blob_sha": "e" * 40, "size_bytes": i,
            "source": "recovery-snapshot",
        })
    for i in range(142):
        path = f"src/extra-{i:03d}.py"
        files[path] = ("f" * 40, i, "100644")
        manifest["inventory"].append({
            "path": path, "git_blob_sha": "f" * 40, "size_bytes": i,
            "source": "m001",
        })
    assert vault.validate_manifest(manifest, files) == (522, 379)
