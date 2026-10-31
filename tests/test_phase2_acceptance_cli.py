"""Regression guards for the existing clean-SHA Phase 2 acceptance CLI."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def test_acceptance_cli_help_is_executable():
    result=subprocess.run([sys.executable,'scripts/phase2_acceptance.py','--help'],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert result.returncode==0
    assert '--expected-sha' in result.stdout

def test_acceptance_cli_rejects_wrong_sha_without_running_tests_or_writing_receipt():
    root=ROOT/'evidence/acceptance'
    before=set(root.glob('phase2-*.json')) if root.exists() else set()
    result=subprocess.run([sys.executable,'scripts/phase2_acceptance.py','--expected-sha','0'*40],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert result.returncode==2
    assert 'ACCEPTANCE: FAIL (expected HEAD' in result.stdout
    assert '--- run ' not in result.stdout
    after=set(root.glob('phase2-*.json')) if root.exists() else set()
    assert before==after
