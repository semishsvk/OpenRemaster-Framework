from pathlib import Path
from copy import deepcopy
import json
import subprocess
import sys
import pytest
from openremaster.manifest import ProjectManifest
from openremaster.naming import read_registry, resolve, resolve_manifest_component, ResolutionError

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"examples/naming/canonical-components.review.json"

def manifest(metadata=None):
    return ProjectManifest("1","openazrael","Legacy unchanged","legacy-adapter",metadata=metadata or {})

def test_existing_manifest_without_reference_stays_unmodified():
    value=manifest({"legacy":"kept"});before=deepcopy(dict(value.metadata))
    assert resolve_manifest_component(value,REGISTRY) is None
    assert value.project_id=="openazrael" and dict(value.metadata)==before

def test_shared_component_reference_preserves_logical_and_legacy_project_ids():
    metadata={"orf_component_ref":"K003","orf_project_id":"OpenRemaster"};value=manifest(metadata)
    result=resolve_manifest_component(value,REGISTRY)
    assert result["manifest_project_id"]=="openazrael"
    assert result["registry_project_id"]=="OpenRemaster" and result["component_id"]=="orf.execution.control"
    assert result["display_name"]=="Execution Control" and value.metadata==metadata
    assert result["owner_admission"] is result["rename_authorized"] is result["execution_authorized"] is False

@pytest.mark.parametrize("metadata",[
    {"orf_component_ref":"K003"},
    {"orf_component_ref":"","orf_project_id":"OpenRemaster"},
    {"orf_component_ref":"K003","orf_project_id":False},
    {"orf_component_ref":"K003","orf_project_id":"OpenRemaster","orf_edition_id":False},
])
def test_malformed_or_unscoped_metadata_is_rejected(metadata):
    with pytest.raises(ValueError):resolve_manifest_component(manifest(metadata),REGISTRY)

def test_project_scope_never_case_normalizes_or_falls_back():
    with pytest.raises(ResolutionError):resolve_manifest_component(manifest({"orf_component_ref":"K003","orf_project_id":"openremaster"}),REGISTRY)

def test_unknown_identity_is_held():
    with pytest.raises(ResolutionError):resolve_manifest_component(manifest({"orf_component_ref":"orf.execution.gateway","orf_project_id":"OpenRemaster"}),REGISTRY)

@pytest.mark.parametrize("project,edition",[("OpenAzrael-Demo","demo"),("OpenAzrael-Retail","retail")])
def test_explicit_editions_remain_separate(project,edition):
    result=resolve_manifest_component(manifest({"orf_component_ref":project,"orf_project_id":project,"orf_edition_id":edition}),REGISTRY)
    assert result["registry_project_id"]==project and result["edition_id"]==edition
    assert result["manifest_project_id"]=="openazrael" and not result["owner_admission"]

def test_missing_edition_cannot_be_inferred_from_directory_or_name():
    with pytest.raises(ValueError):resolve_manifest_component(manifest({"orf_component_ref":"OpenAzrael-Demo","orf_project_id":"OpenAzrael-Demo"}),REGISTRY)

def test_wrong_edition_is_rejected():
    with pytest.raises(ResolutionError):resolve_manifest_component(manifest({"orf_component_ref":"OpenAzrael-Demo","orf_project_id":"OpenAzrael-Demo","orf_edition_id":"retail"}),REGISTRY)

@pytest.mark.parametrize("project",["OpenCyberMage","OpenCybermage"])
def test_existing_case_conflicts_are_not_merged(project):
    with pytest.raises(ResolutionError):resolve_manifest_component(manifest({"orf_component_ref":project,"orf_project_id":project}),REGISTRY)

def test_package_cli_consumes_the_same_existing_registry():
    run=subprocess.run([sys.executable,"-B","-m","openremaster.naming",str(REGISTRY),"--resolve","K003"],capture_output=True,text=True,encoding="utf-8",timeout=20)
    assert run.returncode==0 and json.loads(run.stdout)["display_name"]=="Execution Control"

def test_packaged_contract_keeps_existing_identity_set():
    records=read_registry(REGISTRY)["components"]
    assert len(records)==54 and len({r["component_id"] for r in records})==54
    assert resolve(records,"K003")["component_id"]=="orf.execution.control"

def test_registry_authority_claim_is_not_accepted(tmp_path):
    data=json.loads(REGISTRY.read_text(encoding="utf-8"));data["owner_admission"]=True
    bad=tmp_path/"bad.json";bad.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(ValueError):resolve_manifest_component(manifest({"orf_component_ref":"K003","orf_project_id":"OpenRemaster"}),bad)


def test_example_fixture_contains_no_host_or_ownership_bindings():
    from hashlib import sha256
    data=read_registry(REGISTRY)
    assert data["logical_identity_basis"].startswith("PORTABLE_TEST_FIXTURE_ONLY:")
    expected=sha256((ROOT/"docs/naming-harmonization.md").read_bytes()).hexdigest()
    for row in data["components"]:
        assert all(row[key] is None for key in ["owner","source_path","manifest_path","artifact_id","version"])
        assert row["provenance"]==[{"path":"docs/naming-harmonization.md","sha256":expected,"role":"PORTABLE_EXAMPLE_ONLY_NOT_SOURCE_OR_OWNER_AUTHORITY"}]
    assert data["owner_admission"] is False
