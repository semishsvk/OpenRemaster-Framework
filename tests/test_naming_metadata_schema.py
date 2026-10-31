"""Keep the optional metadata schema aligned with resolver edition semantics."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from openremaster.manifest import ProjectManifest
from openremaster.naming import resolve_manifest_component

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'examples/naming/canonical-components.review.json'
VALIDATOR = Draft202012Validator(json.loads((ROOT / 'examples/naming/metadata.schema.json').read_bytes()))

def manifest(metadata):
    return ProjectManifest('1', 'legacy-project', 'Legacy project', 'existing-adapter', metadata=metadata)

def test_null_shared_edition_matches_omitted_edition():
    omitted = {'orf_component_ref': 'K003', 'orf_project_id': 'OpenRemaster'}
    explicit_null = {**omitted, 'orf_edition_id': None}
    assert VALIDATOR.is_valid(omitted) and VALIDATOR.is_valid(explicit_null)
    assert resolve_manifest_component(manifest(omitted), REGISTRY) == resolve_manifest_component(manifest(explicit_null), REGISTRY)

@pytest.mark.parametrize('project', ['OpenAzrael-Demo', 'OpenAzrael-Retail'])
def test_null_never_supplies_an_edition_specific_identity(project):
    metadata = {'orf_component_ref': project, 'orf_project_id': project, 'orf_edition_id': None}
    assert VALIDATOR.is_valid(metadata)
    with pytest.raises(ValueError, match='Explicit edition required'):
        resolve_manifest_component(manifest(metadata), REGISTRY)

@pytest.mark.parametrize('value', ['', ' ', False, 0, [], {}])
def test_invalid_edition_remains_rejected_by_schema_and_runtime(value):
    metadata = {'orf_component_ref': 'K003', 'orf_project_id': 'OpenRemaster', 'orf_edition_id': value}
    assert not VALIDATOR.is_valid(metadata)
    with pytest.raises(ValueError, match='Explicit edition must be a nonempty string'):
        resolve_manifest_component(manifest(metadata), REGISTRY)
