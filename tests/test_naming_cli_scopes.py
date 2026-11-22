"""Explicit naming scopes must not silently become unfiltered registry summaries."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'examples/naming/canonical-components.review.json'


def run_cli(tmp_path, options, registry=REGISTRY):
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT / 'src')
    return subprocess.run(
        [sys.executable, '-B', '-m', 'openremaster.naming', str(registry), *options],
        cwd=tmp_path, env=env, capture_output=True, text=True, encoding='utf-8', timeout=20,
    )


@pytest.mark.parametrize('options', [
    ['--project', 'OpenAzrael-Demo'],
    ['--edition', 'retail'],
    ['--project', 'OpenAzrael-Retail', '--edition', 'retail'],
    ['--project', 'OpenCyberMage'],
    ['--project', 'OpenCybermage'],
])
def test_scope_without_selector_never_returns_an_unfiltered_summary(tmp_path, options):
    result = run_cli(tmp_path, options)
    assert result.returncode == 75
    assert json.loads(result.stdout) == {'status': 'HOLD', 'reason': 'PROJECT_EDITION_SCOPE_REQUIRES_RESOLVE'}


@pytest.mark.parametrize('options', [
    ['--resolve', ''], ['--resolve', ' '], ['--resolve', '\t'],
    ['--project', ''], ['--edition', ' '],
    ['--resolve', 'K003', '--project', ''],
    ['--resolve', 'K003', '--edition', '\t'],
])
def test_empty_selector_or_scope_never_falls_back(tmp_path, options):
    result = run_cli(tmp_path, options)
    assert result.returncode == 75
    assert json.loads(result.stdout) == {'status': 'HOLD', 'reason': 'EMPTY_SELECTION_OR_SCOPE'}


def test_invalid_scope_is_refused_before_reading_the_registry(tmp_path):
    result = run_cli(tmp_path, ['--project', 'OpenAzrael-Demo'], tmp_path / 'not-present.json')
    assert result.returncode == 75
    assert json.loads(result.stdout)['reason'] == 'PROJECT_EDITION_SCOPE_REQUIRES_RESOLVE'


@pytest.mark.parametrize('options,component,project,edition', [
    (['--resolve', 'K003'], 'orf.execution.control', 'OpenRemaster', None),
    (['--resolve', 'K003', '--project', 'OpenRemaster'], 'orf.execution.control', 'OpenRemaster', None),
    (['--resolve', 'OpenAzrael', '--project', 'OpenAzrael'], 'orf.project.openazrael', 'OpenAzrael', None),
    (['--resolve', 'OpenAzrael-Demo', '--project', 'OpenAzrael-Demo', '--edition', 'demo'], 'orf.project.openazraeldemo', 'OpenAzrael-Demo', 'demo'),
    (['--resolve', 'OpenAzrael-Retail', '--project', 'OpenAzrael-Retail', '--edition', 'retail'], 'orf.project.openazraelretail', 'OpenAzrael-Retail', 'retail'),
])
def test_existing_explicit_resolution_preserves_exact_identity(tmp_path, options, component, project, edition):
    result = run_cli(tmp_path, options)
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert (value['component_id'], value['project_id'], value['edition_id']) == (component, project, edition)


@pytest.mark.parametrize('options', [
    ['--resolve', 'K003', '--project', 'OpenAzrael-Demo'],
    ['--resolve', 'K003', '--edition', 'retail'],
    ['--resolve', 'OpenAzrael-Demo', '--project', 'OpenAzrael-Retail', '--edition', 'retail'],
    ['--resolve', 'OpenAzrael-Retail', '--project', 'OpenAzrael-Retail', '--edition', 'demo'],
    ['--resolve', 'OpenCyberMage', '--project', 'OpenCybermage'],
    ['--resolve', ' K003 '],
])
def test_conflicting_and_nonexact_scopes_stay_held(tmp_path, options):
    result = run_cli(tmp_path, options)
    assert result.returncode == 75
    assert json.loads(result.stdout)['status'] == 'HOLD'


def test_no_option_registry_summary_remains_supported(tmp_path):
    result = run_cli(tmp_path, [])
    assert result.returncode == 0
    value = json.loads(result.stdout)
    assert value['valid'] is True and value['components'] == 54
