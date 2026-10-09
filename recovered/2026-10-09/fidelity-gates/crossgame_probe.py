"""Read-only corpus-specific regression fixtures for the new framework gates.
Only extracts a few small representative Fallout 2 files, never modifies source.
"""
import hashlib
import json
from pathlib import Path
import struct
import zlib

from alignment import hash_file
from semantics import normalize_resource_path, resolve_resources

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r"F:\Remaster Framework\source\Fallout 2")


def dat2_index(path):
    total = path.stat().st_size
    with path.open("rb") as f:
        f.seek(-8, 2)
        directory_bytes, declared_total = struct.unpack("<II", f.read(8))
        if declared_total != total or not 8 < directory_bytes < total:
            raise ValueError("DAT2_FOOTER_INVALID")
        directory_start = total - 8 - directory_bytes
        f.seek(directory_start)
        count = struct.unpack("<I", f.read(4))[0]
        records = {}
        for _ in range(count):
            n = struct.unpack("<I", f.read(4))[0]
            if n > 512:
                raise ValueError("DAT2_NAME_TOO_LONG")
            name = f.read(n).decode("latin1")
            flag = f.read(1)[0]
            unpacked, packed, offset = struct.unpack("<III", f.read(12))
            if flag not in (0, 1) or offset + packed > directory_start:
                raise ValueError("DAT2_ENTRY_OUT_OF_BOUNDS")
            key = normalize_resource_path(name)
            records.setdefault(key, []).append((flag, unpacked, packed, offset))
        if f.tell() != total - 8:
            raise ValueError("DAT2_DIRECTORY_LENGTH_MISMATCH")
        return records


def content(path, record):
    flag, unpacked, packed, offset = record
    with path.open("rb") as f:
        f.seek(offset)
        data = f.read(packed)
    payload = zlib.decompress(data) if flag else data
    if len(payload) != unpacked:
        raise ValueError("DAT2_DECOMPRESSED_LENGTH_MISMATCH")
    return payload


def main():
    master, patch = SOURCE / "master.dat", SOURCE / "patch000.dat"
    master_records, patch_records = dat2_index(master), dat2_index(patch)
    # Previous independently inventoried authoritative corpus fingerprints.
    expected_source_sha = {
        "master": "9b096d3035edafd4077deeb8ee7877a803b9db98497aa4596624b5c058a84711",
        "patch": "16122a47d9fa1fb2f490d1fb38bb1b7eb8ca8edcf2c06a2c9d78beed812ff564"}
    for role, path in (("master", master), ("patch", patch)):
        if hash_file(path).lower() != expected_source_sha[role]:
            raise ValueError("CANONICAL_FALLOUT2_CORPUS_FINGERPRINT_CHANGED")
    overlap = sorted(master_records.keys() & patch_records.keys())
    if not overlap:
        raise ValueError("EXPECTED_FALLOUT2_OVERLAP_NOT_FOUND")
    selected = overlap[:12]
    entries = {}
    for role, path, rows in (("patch", patch, patch_records), ("master", master, master_records)):
        selected_rows = []
        for name in selected:
            record = rows[name][0]
            payload = content(path, record)
            selected_rows.append({"path": name, "size": len(payload),
                                  "sha256": hashlib.sha256(payload).hexdigest()})
        entries[role] = selected_rows
    proof = {
        "schema": "OpenFallout2.Dat2ResourceOverlapEvidence.v1",
        "status": "STRUCTURAL_CORPUS_OVERLAP",
        "source_read_only": True,
        "archive_sha256": {"master": hash_file(master), "patch": hash_file(patch)},
        "directory_entries": {"master": sum(map(len, master_records.values())),
                              "patch": sum(map(len, patch_records.values()))},
        "overlapping_paths": len(overlap),
        "sample_paths": selected,
        "sample_decoded": entries,
        "warning": "Runtime precedence NOT proven by this structural sample."}
    proof_path = ROOT / "evidence" / "fallout2_resource_overlap.json"
    proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema": "ResourceResolutionContract.v1",
        "game": "OpenFallout2",
        "resolution_order": ["patch", "master"],
        "order_evidence_state": "HYPOTHESIS",
        "order_evidence_path": proof_path.name,
        "order_evidence_sha256": hash_file(proof_path),
        "layers": [
            {"id": "patch", "source_sha256": proof["archive_sha256"]["patch"], "entries": entries["patch"]},
            {"id": "master", "source_sha256": proof["archive_sha256"]["master"], "entries": entries["master"]}]}
    checked = resolve_resources(manifest, selected, ROOT / "evidence")
    if checked["status"] != "STRUCTURAL_ONLY":
        raise ValueError("HYPOTHESIS_ILLEGALLY_PROMOTED")
    (ROOT / "fixtures" / "fallout2_resource_hypothesis.json").write_text(
        json.dumps({**manifest, "requested": selected}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    result = {"schema": "OpenFallout2.CrossgameGuardFixture.v1", "status": "PASS",
              "directory_entries": proof["directory_entries"],
              "overlapping_paths": len(overlap), "sample_count": len(selected),
              "resource_gate_status": checked["status"], "runtime_fidelity": "NOT_TESTED"}
    print(json.dumps(result, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
