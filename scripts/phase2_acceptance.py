from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


def _run_once(index: int) -> dict[str, object]:
    command = [sys.executable, "-m", "pytest", "-q"]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    output = result.stdout + result.stderr
    print(f"--- run {index} ---")
    print(output, end="" if output.endswith("\n") else "\n")
    return {
        "run": index,
        "command": command,
        "exit_code": result.returncode,
        "output_sha256": sha256(output.encode("utf-8")).hexdigest(),
    }


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    expected = args.expected_sha
    head = _git("rev-parse", "HEAD")
    if head != expected:
        print(f"ACCEPTANCE: FAIL (expected HEAD {expected}, got {head})")
        return 2
    if _git("status", "--porcelain"):
        print("ACCEPTANCE: FAIL (working tree is not clean)")
        return 2

    runs = (_run_once(1), _run_once(2))
    passed = all(run["exit_code"] == 0 for run in runs)
    payload = {
        "schema_version": "1",
        "phase": "phase2-p2.1-p2.5",
        "tested_sha": head,
        "working_tree_clean": True,
        "runs": runs,
        "accepted": passed,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    evidence_dir = Path("evidence/acceptance")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / f"phase2-{head[:12]}.json"
    path.write_text(encoded, encoding="utf-8")
    print("evidence:", path)
    print("evidence_sha256:", sha256(encoded.encode("utf-8")).hexdigest())
    print("ACCEPTANCE:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
