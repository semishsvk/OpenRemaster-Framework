"""Wire schema negatives; schema validation never establishes independent trust."""
import copy
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator,FormatChecker,ValidationError
ROOT=Path(__file__).resolve().parent.parent/'contracts/dual-trust/v1'
def validator(name):return Draft202012Validator(json.loads((ROOT/name).read_text()),format_checker=FormatChecker())
def worker():return dict(schema='OpenRemaster.WorkerObservation.v1',worker_identity='synthetic',trust_class='DEVELOPMENT',capabilities=['build_studio_dev'],project_scope=['fixture'],environment='synthetic-only',owner_lease=None,resource_allocation=None,admission_status='UNKNOWN',attestation_status='MISSING',last_verified_heartbeat=None,current_task=None,checkpoint=None,audit_references=[],release_eligible=False)
def handoff():return dict(schema='OpenRemaster.ReleaseHandoff.v1',repository='fixture',commit='a'*40,project='fixture',build_recipe_sha256='b'*64,dependencies_sha256='c'*64,test_profile='synthetic',candidate_evidence=['fixture'],source_integrity=['fixture'],fidelity_requirements=['fixture'],security_policy_version='test',release_request='unverified-reference')
def test_complete_untrusted_metadata_is_only_structurally_valid():validator('worker-observation.schema.json').validate(worker())
def test_no_metadata_trust_escalation_to_release_eligibility():
    doc=worker();doc.update(trust_class='SECURE_PRODUCTION',release_eligible=True)
    with pytest.raises(ValidationError):validator('worker-observation.schema.json').validate(doc)
def test_credentials_cannot_be_smuggled_into_observation():
    doc=worker();doc['production_private_key']='fixture'
    with pytest.raises(ValidationError):validator('worker-observation.schema.json').validate(doc)
def test_heartbeat_format_rejected():
    doc=worker();doc['last_verified_heartbeat']='yesterday'
    with pytest.raises(ValidationError):validator('worker-observation.schema.json').validate(doc)
def test_handoff_requires_every_binding():
    v=validator('release-handoff.schema.json');doc=handoff();v.validate(doc)
    for key in doc:
        bad=copy.deepcopy(doc);del bad[key]
        with pytest.raises(ValidationError):v.validate(bad)
@pytest.mark.parametrize('commit',['main','a'*39,'+'+'a'*39,'a'*40+'\n'])
def test_mutable_or_noncanonical_revision_denied(commit):
    doc=handoff();doc['commit']=commit
    with pytest.raises(ValidationError):validator('release-handoff.schema.json').validate(doc)
