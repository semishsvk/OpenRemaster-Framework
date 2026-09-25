from hashlib import sha256
import pytest
from openremaster.visual import CameraPose, RenderConfig, VisualArtifact, VisualCaptureContract
from openremaster.visual_baseline import VisualBaseline
from openremaster.visual_compare import compare_visual_artifacts

def contract(lighting="original-1996"):
    return VisualCaptureContract(
        "1", "openazrael", "sha", "room-1", "overview",
        CameraPose((0.0, 1.7, 0.0), (0.0, 90.0, 0.0), 70.0),
        RenderConfig(1920, 1080, lighting, "godot", "4.x"),
        "world-state"
    )

def artifact(c, content=b"image"):
    return VisualArtifact(c.digest(), sha256(content).hexdigest(), "png", len(content))

def test_contract_digest_is_deterministic():
    assert contract().digest() == contract().digest()

def test_original_and_neutral_lighting_are_distinct_contracts():
    assert contract("original-1996").digest() != contract("neutral").digest()

def test_baseline_requires_exact_contract_binding():
    c = contract()
    wrong = artifact(contract("neutral"))
    with pytest.raises(ValueError, match="not bound"):
        VisualBaseline("room-1-original", c, wrong).validate()

def test_exact_visual_match():
    c = contract()
    assert compare_visual_artifacts(artifact(c), artifact(c)).exact_match

def test_same_contract_different_image_is_regression_candidate():
    c = contract()
    result = compare_visual_artifacts(artifact(c, b"a"), artifact(c, b"b"))
    assert result.comparable
    assert not result.exact_match

def test_different_contracts_are_not_compared():
    result = compare_visual_artifacts(artifact(contract()), artifact(contract("neutral")))
    assert not result.comparable
