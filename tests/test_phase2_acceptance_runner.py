"""Phase 2 runner controls, with no actual subprocess or heavy pytest run."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "phase2_acceptance.py"
spec = importlib.util.spec_from_file_location("phase2_acceptance", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_mismatched_revision_fails_before_testing(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["phase2_acceptance.py", "--expected-sha", "c" * 40])
    monkeypatch.setattr(runner, "_git", lambda *args: "a" * 40 if args == ("rev-parse", "HEAD") else "")
    monkeypatch.setattr(runner, "_run_once", lambda *_: pytest.fail("test run must not execute"))
    assert runner.main() == 2


def test_dirty_worktree_fails_before_testing(monkeypatch):
    sha = "a" * 40
    monkeypatch.setattr(sys, "argv", ["phase2_acceptance.py", "--expected-sha", sha])
    monkeypatch.setattr(runner, "_git", lambda *args: sha if args == ("rev-parse", "HEAD") else " M src/test.py")
    monkeypatch.setattr(runner, "_run_once", lambda *_: pytest.fail("test run must not execute"))
    assert runner.main() == 2


def test_two_passes_emit_sha_bound_receipt(monkeypatch, tmp_path):
    sha = "a" * 40
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["phase2_acceptance.py", "--expected-sha", sha])
    monkeypatch.setattr(runner, "_git", lambda *args: sha if args == ("rev-parse", "HEAD") else "")
    calls = []

    def fake_run(index):
        calls.append(index)
        return {"run": index, "command": ["python", "-m", "pytest", "-q"], "exit_code": 0, "output_sha256": "f" * 64}

    monkeypatch.setattr(runner, "_run_once", fake_run)
    assert runner.main() == 0
    receipt = json.loads((tmp_path / "evidence" / "acceptance" / f"phase2-{sha[:12]}.json").read_text())
    assert receipt["tested_sha"] == sha
    assert receipt["accepted"] is True
    assert [r["run"] for r in receipt["runs"]] == [1, 2]
    assert calls == [1, 2]


def test_failed_run_keeps_failure_evidence(monkeypatch, tmp_path):
    sha = "a" * 40
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["phase2_acceptance.py", "--expected-sha", sha])
    monkeypatch.setattr(runner, "_git", lambda *args: sha if args == ("rev-parse", "HEAD") else "")
    monkeypatch.setattr(runner, "_run_once", lambda index: {"run": index, "exit_code": 1 if index == 2 else 0})
    assert runner.main() == 1
    receipt = json.loads((tmp_path / "evidence" / "acceptance" / f"phase2-{sha[:12]}.json").read_text())
    assert receipt["accepted"] is False
