"""Keep the portable schema's machine-string syntax aligned with the existing reader."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from openremaster.naming import read_registry, validate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'examples/naming/canonical-components.review.json'
SCHEMA = json.loads((ROOT / 'examples/naming/canonical-components.schema.json').read_bytes())
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA)
SUFFIXES = ['\n', '\r', '\r\n', '\u2028', '\u2029', '\0']


def test_existing_portable_registry_passes_schema_and_reader():
    data = read_registry(FIXTURE)
    assert VALIDATOR.is_valid(data)
    assert len(data['components']) == 54


@pytest.mark.parametrize('suffix', SUFFIXES)
@pytest.mark.parametrize('field', ['component_id', 'dependency', 'provenance_sha256'])
def test_machine_strings_cannot_gain_a_final_line_terminator(field, suffix):
    data = read_registry(FIXTURE)
    row = data['components'][0]
    if field == 'component_id':
        row['component_id'] += suffix
    elif field == 'dependency':
        row['dependencies'] = [data['components'][1]['component_id'] + suffix]
    else:
        row['provenance'][0]['sha256'] += suffix
    assert not VALIDATOR.is_valid(data)
    with pytest.raises(ValueError):
        validate(data['components'])


def test_every_registered_machine_identity_retains_its_exact_spelling():
    data = read_registry(FIXTURE)
    identity_schema = SCHEMA['properties']['components']['items']['properties']['component_id']
    checker = Draft202012Validator(identity_schema)
    for row in data['components']:
        assert checker.is_valid(row['component_id'])
    assert len({row['component_id'] for row in data['components']}) == 54
    projects = {row['project_id'] for row in data['components']}
    assert {'OpenAzrael-Demo', 'OpenAzrael-Retail', 'OpenCyberMage', 'OpenCybermage'} <= projects


def test_structural_schema_does_not_replace_runtime_reference_checks():
    data = read_registry(FIXTURE)
    duplicate = deepcopy(data)
    duplicate['components'].append(deepcopy(duplicate['components'][0]))
    dangling = deepcopy(data)
    dangling['components'][0]['dependencies'] = ['orf.not.registered']
    for value in [duplicate, dangling]:
        assert VALIDATOR.is_valid(value)
        with pytest.raises(ValueError):
            validate(value['components'])


def test_human_display_text_is_not_restricted_to_machine_identifiers():
    data = read_registry(FIXTURE)
    data['components'][0]['display_name'] = 'Framework Core — Source review'
    assert VALIDATOR.is_valid(data)
    assert validate(data['components']) is True
