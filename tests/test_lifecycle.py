from dataclasses import replace
from hashlib import sha256

import pytest

from openremaster.freshness import EvidenceFreshness, Freshness
from openremaster.identity import EvidenceIdentity
from openremaster.lifecycle import EvidenceStage, LifecycleEvidence


def d(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def identity() -> EvidenceIdentity:
    return EvidenceIdentity("2", "opencadaver", "cadaver-retail", "type2-86",
                            "room-000", "default", "run-001", "sha", d("deps"))


def evidence(stage=EvidenceStage.OBSERVED) -> LifecycleEvidence:
    return LifecycleEvidence(identity(), stage, d("evidence"))


def test_supported_positive_chain_observed_to_derived_to_validated():
    observed = evidence()
    derived = observed.transition(EvidenceStage.DERIVED)
    validated = derived.transition(EvidenceStage.VALIDATED)
    assert (observed.stage, derived.stage, validated.stage) == (
        EvidenceStage.OBSERVED, EvidenceStage.DERIVED, EvidenceStage.VALIDATED)


def test_hypothesis_can_be_promoted_only_through_explicit_transition():
    hypothesis = evidence(EvidenceStage.HYPOTHESIS)
    assert hypothesis.transition(EvidenceStage.DERIVED).stage is EvidenceStage.DERIVED
    assert hypothesis.transition(EvidenceStage.VALIDATED).stage is EvidenceStage.VALIDATED


@pytest.mark.parametrize("stage", (EvidenceStage.VALIDATED, EvidenceStage.REJECTED))
def test_terminal_states_fail_closed(stage):
    item = evidence(stage)
    if stage is EvidenceStage.REJECTED:
        item = replace(item, reason="contradicted by corpus")
    with pytest.raises(ValueError, match="invalid evidence lifecycle transition"):
        item.transition(EvidenceStage.OBSERVED)


def test_rejected_requires_reason():
    with pytest.raises(ValueError, match="requires reason"):
        evidence().transition(EvidenceStage.REJECTED)


def test_validated_current_evidence_is_usable():
    item = evidence(EvidenceStage.VALIDATED)
    item.require_usable(EvidenceFreshness(item.evidence_id, Freshness.CURRENT))


def test_stale_validated_evidence_is_not_usable():
    item = evidence(EvidenceStage.VALIDATED)
    with pytest.raises(ValueError, match="stale"):
        item.require_usable(EvidenceFreshness(item.evidence_id, Freshness.STALE, (d("root"),)))


@pytest.mark.parametrize("stage", (
    EvidenceStage.OBSERVED, EvidenceStage.DERIVED,
    EvidenceStage.HYPOTHESIS, EvidenceStage.REJECTED,
))
def test_nonvalidated_current_evidence_is_not_usable(stage):
    item = evidence(stage)
    if stage is EvidenceStage.REJECTED:
        item = replace(item, reason="contradicted")
    with pytest.raises(ValueError, match="not validated"):
        item.require_usable(EvidenceFreshness(item.evidence_id, Freshness.CURRENT))


def test_freshness_must_belong_to_same_evidence():
    item = evidence(EvidenceStage.VALIDATED)
    with pytest.raises(ValueError, match="identity mismatch"):
        item.require_usable(EvidenceFreshness(d("other"), Freshness.CURRENT))
