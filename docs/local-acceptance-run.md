# Local Phase 1 acceptance run

Phase 1 acceptance does not depend on GitHub Actions.

From a clean checkout of the framework branch:

    python -m pip install -e .
    python -m pip install pytest
    python scripts/phase1_acceptance.py

The runner executes the complete pytest suite and exits non-zero on any failure.

A PASS is meaningful only when recorded together with the exact framework commit SHA. The runner does not modify OpenAzrael or OpenCadaver and requires no access to either project.

Until an actual execution result exists for the current HEAD, Phase 1 remains feature-frozen but not merge-ready.
