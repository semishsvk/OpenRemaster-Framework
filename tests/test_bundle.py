from hashlib import sha256
import pytest
from openremaster.bundle import ArtifactRef, ReplayEvidenceBundle
from openremaster.replay import InputFrame, ReplayContract
from openremaster.trace import RuntimeEvent, RuntimeTrace, StateCheckpoint

def replay():
    return ReplayContract("1", "p", "sha", "godot", "4", 60, 7, (InputFrame(0),))

def bundle():
    r = replay()
    t = RuntimeTrace(r.digest(), (RuntimeEvent(0, "spawn", "player"),), (StateCheckpoint(0, "state"),))
    artifact = ArtifactRef("runtime-log", sha256(b"log").hexdigest(), "artifacts/run.log")
    return ReplayEvidenceBundle("1", r, t, (artifact,))

def test_bundle_digest_is_deterministic():
    assert bundle().digest() == bundle().digest()

def test_trace_must_match_replay():
    b = bundle()
    bad = ReplayEvidenceBundle("1", b.replay, RuntimeTrace("wrong"), b.artifacts)
    with pytest.raises(ValueError, match="not bound"):
        bad.validate()

def test_artifact_digest_is_required():
    b = bundle()
    bad = ReplayEvidenceBundle("1", b.replay, b.trace, (ArtifactRef("log", "short"),))
    with pytest.raises(ValueError, match="sha256"):
        bad.validate()
