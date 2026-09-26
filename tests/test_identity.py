from dataclasses import replace
from hashlib import sha256

import pytest

from openremaster.identity import EvidenceIdentity


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def identity() -> EvidenceIdentity:
    return EvidenceIdentity(
        "2", "opencadaver", "cadaver-retail", "room-000-render",
        "room-000", "default", "run-001", "source-sha", digest("deps"),
    )


def test_identity_is_deterministic_and_sha_bound():
    value = identity()
    assert value.digest() == replace(value).digest()
    assert len(value.digest()) == 64


@pytest.mark.parametrize("field", (
    "project_id", "corpus_id", "artifact_id", "room_id",
    "state_id", "run_id", "source_revision", "dependency_digest",
))
def test_each_identity_field_changes_digest(field):
    value = identity()
    replacement = digest("other") if field == "dependency_digest" else "other"
    assert replace(value, **{field: replacement}).digest() != value.digest()


@pytest.mark.parametrize("field", (
    "project_id", "corpus_id", "room_id", "state_id",
    "run_id", "source_revision", "dependency_digest",
))
def test_cross_context_mismatch_fails_closed(field):
    value = identity()
    replacement = digest("other") if field == "dependency_digest" else "other"
    with pytest.raises(ValueError, match=field):
        value.require_same_context(replace(value, artifact_id="another-artifact", **{field: replacement}))


def test_distinct_artifacts_can_share_exact_context():
    value = identity()
    value.require_same_context(replace(value, artifact_id="room-000-replay"))


@pytest.mark.parametrize("field", (
    "project_id", "corpus_id", "artifact_id", "room_id",
    "state_id", "run_id", "source_revision",
))
def test_required_identity_fields_reject_empty(field):
    with pytest.raises(ValueError, match=field):
        replace(identity(), **{field: ""}).validate()


def test_dependency_digest_requires_sha256_hex():
    with pytest.raises(ValueError, match="sha256"):
        replace(identity(), dependency_digest="not-a-digest").validate()
