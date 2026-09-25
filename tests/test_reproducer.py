from hashlib import sha256
from openremaster.bundle import ArtifactRef, ReplayEvidenceBundle
from openremaster.replay import InputFrame, ReplayContract
from openremaster.reproducer import verify_reproduction
from openremaster.trace import RuntimeTrace

def test_exact_bundle_is_reproducible():
    replay = ReplayContract("1", "p", "sha", "runtime", "1", 60, 0, (InputFrame(0),))
    bundle = ReplayEvidenceBundle(
        "1", replay, RuntimeTrace(replay.digest()),
        (ArtifactRef("log", sha256(b"x").hexdigest()),)
    )
    assert verify_reproduction(bundle.digest(), bundle).reproducible

def test_different_source_revision_breaks_reproduction():
    a = ReplayContract("1", "p", "sha-a", "runtime", "1", 60, 0, (InputFrame(0),))
    b = ReplayContract("1", "p", "sha-b", "runtime", "1", 60, 0, (InputFrame(0),))
    expected = ReplayEvidenceBundle("1", a, RuntimeTrace(a.digest()))
    observed = ReplayEvidenceBundle("1", b, RuntimeTrace(b.digest()))
    assert not verify_reproduction(expected.digest(), observed).reproducible
