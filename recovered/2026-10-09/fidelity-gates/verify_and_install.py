"""Deterministic software-only release/rehydration and isolated installation.
No edits to active ORCH-K003 shared validator, worker, or canonical source.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
FRAMEWORK = Path(r"F:\Remaster Framework")
DEST = FRAMEWORK / "orchestrator" / "fidelity-gates-v1"
OUT = FRAMEWORK / "output" / "framework"
RELEASE = "ORF-FIDELITY-GATES-20261009-r1"


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as fd:
        for part in iter(lambda: fd.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def files(root):
    return sorted(p for p in root.rglob("*") if p.is_file() and
                  "__pycache__" not in p.parts and
                  (p.suffix.lower() in (".py", ".json", ".md")) and
                  not p.name.startswith("CHECKPOINT"))


def fingerprint(root):
    records = []
    for path in files(root):
        name = path.relative_to(root).as_posix()
        records.append({"path": name, "size": path.stat().st_size, "sha256": hash_file(path)})
    return records


def digest_records(rows):
    data = "".join(f'{r["path"]}|{r["size"]}|{r["sha256"]}\n' for r in rows)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def test(root):
    c = subprocess.run([sys.executable, "-m", "unittest", "discover",
                        "-s", str(root), "-p", "test_*.py", "-q"],
                       capture_output=True, text=True, timeout=80)
    output = (c.stdout or "") + "\n" + (c.stderr or "")
    match = re.search(r"Ran (\d+) tests", output)
    count = int(match.group(1)) if match else -1
    if c.returncode != 0 or count < 90 or "OK" not in output:
        raise RuntimeError("SUITE_FAILED: " + output[-2500:])
    return {"exit_code": c.returncode, "tests": count, "output": output[-1500:]}


def main():
    if "source" in (x.lower() for x in ROOT.parts):
        raise RuntimeError("STAGING_NOT_IN_READONLY_SOURCE")
    source_dir = FRAMEWORK / "source" / "Fallout 2"
    corpus_pins = {"master.dat": "9b096d3035edafd4077deeb8ee7877a803b9db98497aa4596624b5c058a84711",
                   "patch000.dat": "16122a47d9fa1fb2f490d1fb38bb1b7eb8ca8edcf2c06a2c9d78beed812ff564"}
    for name, known in corpus_pins.items():
        if hash_file(source_dir / name) != known:
            raise RuntimeError("CANONICAL_CORPUS_HASH_CHANGED:" + name)
    control_files = [FRAMEWORK / "orchestrator" / "control-plane" / n
                     for n in ("orch_k003.py", "validator.py", "framework-vnext-policies.json")]
    before = {str(x): hash_file(x) for x in control_files}
    # The cross-game experiment creates only isolated evidence/fixtures.
    cross = subprocess.run([sys.executable, str(ROOT / "crossgame_probe.py")],
                           capture_output=True, text=True, timeout=60)
    if cross.returncode:
        raise RuntimeError("CROSSGAME_PROBE_FAILED:" + cross.stderr[-1200:])
    pre = test(ROOT)
    rows = fingerprint(ROOT)
    digest = digest_records(rows)
    release_packages = OUT / "packages"
    release_evidence = OUT / "evidence" / RELEASE
    release_packages.mkdir(parents=True, exist_ok=True)
    release_evidence.mkdir(parents=True, exist_ok=True)
    package = release_packages / (RELEASE + ".zip")
    if package.exists():
        raise RuntimeError("RELEASE_PACKAGE_ALREADY_EXISTS_NO_OVERWRITE")
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in rows:
            archive.write(ROOT / entry["path"], arcname=entry["path"])
    restore_results = []
    with tempfile.TemporaryDirectory(prefix="orf-fidelity-gates-restore-",
                                     dir=FRAMEWORK / "work" / "_staging") as td:
        for label in ("restore-a", "restore-b"):
            target = Path(td) / label
            target.mkdir()
            with zipfile.ZipFile(package, "r") as archive:
                archive.extractall(target)
            restored = fingerprint(target)
            if restored != rows or digest_records(restored) != digest:
                raise RuntimeError("REHYDRATION_FINGERPRINT_MISMATCH:" + label)
            trial = test(target)
            restore_results.append({"label": label, "tests": trial["tests"],
                                    "exit_code": trial["exit_code"],
                                    "tree_sha256": digest})
    if DEST.exists():
        if fingerprint(DEST) != rows:
            raise RuntimeError("CANONICAL_VERSIONED_TARGET_ALREADY_EXISTS_DIFFERENT")
        install = "PRESENT_IDENTICAL"
    else:
        DEST.mkdir(parents=True)
        for entry in rows:
            target = DEST / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / entry["path"], target)
        install = "CREATED_VERSIONED_NAMESPACE"
    if fingerprint(DEST) != rows:
        raise RuntimeError("INSTALLED_FILE_FINGERPRINT_MISMATCH")
    canonical_tests = test(DEST)
    after = {str(x): hash_file(x) for x in control_files}
    if before != after:
        raise RuntimeError("SHARED_CONTROL_PLANE_CHANGED_DURING_RELEASE_RECONCILE_REQUIRED")
    for name, known in corpus_pins.items():
        if hash_file(source_dir / name) != known:
            raise RuntimeError("SOURCE_HASH_CHANGED_AFTER_RELEASE:" + name)
    receipt = {
        "schema": "OpenRemaster.FidelityGatesCheckpoint.v1",
        "release": RELEASE, "status": "SOFTWARE_CONTRACT_PASS_PRODUCTION_HOLD",
        "utc": datetime.now(timezone.utc).isoformat(),
        "source_staging": str(ROOT), "installed_namespace": str(DEST),
        "installation": install, "shared_control_plane_files_modified": False,
        "phase1_frozen_unchanged": True,
        "contracts": ["OracleAlignmentContract.v1", "ComparisonAdmissibilityGuard.v1",
                      "CausalFidelityDiff.v1", "ResourceResolutionContract.v1",
                      "SemanticPopulationGuard.v1"],
        "code_and_fixture_tree_sha256": digest,
        "files": rows,
        "package": str(package), "package_sha256": hash_file(package),
        "tests": {"staging": pre["tests"], "installed": canonical_tests["tests"],
                  "two_restores": restore_results, "exit_codes": [0, 0, 0, 0]},
        "real_fixture": json.loads(cross.stdout.strip().splitlines()[-1]),
        "canonical_source_readonly": True,
        "canonical_source_fingerprints": corpus_pins,
        "shared_control_plane_sha256": before,
        "native_worker_jobs_started": 0,
        "production_gate": {"status": "HOLD",
                            "reason": "OWNER_WIRED_ORCH_K003_PLUS_ALIGNED_RETAIL_E2E_PENDING",
                            "existing_active_validator_untouched": True,
                            "opt_in_adapter_available": True,
                            "fidelity_verified": False},
        "rehydration_recipe": "Extract zip then python -m unittest discover -s EXTRACTED -p test_*.py -q"
    }
    checkpoint = release_evidence / "CHECKPOINT.json"
    checkpoint.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (release_evidence / "TESTS.txt").write_text(pre["output"] + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "checkpoint": str(checkpoint),
                      "package": str(package), "file_count": len(rows),
                      "source_tree_sha256": digest, "tests": receipt["tests"],
                      "production_gate": receipt["production_gate"]}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"status": "RELEASE_BLOCKED", "error": str(e)}))
        sys.exit(1)
