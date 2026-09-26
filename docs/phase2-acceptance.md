# Local Phase 2 P2.1-P2.5 acceptance

Phase 2 acceptance is local-first and does not require GitHub Actions.

From a clean checkout of the exact Phase 2 checkpoint:

    python -m pip install -e .
    python -m pip install pytest
    SHA=$(git rev-parse HEAD)
    python scripts/phase2_acceptance.py --expected-sha "$SHA"

The runner refuses a SHA mismatch or dirty working tree, executes the complete pytest suite twice, and writes a canonical SHA-bound JSON evidence record under `evidence/acceptance/`.

P2.1-P2.5 may be marked ACCEPTED only when both runs exit 0. A failed run must remain evidence of failure; fix the code, commit a new SHA, and rerun against that new exact SHA.
