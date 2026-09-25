from __future__ import annotations
import subprocess
import sys

def main() -> int:
    command = [sys.executable, "-m", "pytest", "-q"]
    print("OpenRemaster Framework Phase 1 acceptance")
    print("command:", " ".join(command))
    result = subprocess.run(command, check=False)
    if result.returncode:
        print("ACCEPTANCE: FAIL")
        return result.returncode
    print("ACCEPTANCE: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
