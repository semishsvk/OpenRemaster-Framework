import pytest
from openremaster.replay import InputFrame, ReplayContract

def contract():
    return ReplayContract(
        "1", "openazrael", "abc123", "godot", "4.x", 60, 42,
        (
            InputFrame(0, ("move_forward",), (("look_x", 0.0),)),
            InputFrame(1, ("interact",), ()),
        ),
    )

def test_replay_digest_is_deterministic():
    assert contract().digest() == contract().digest()

def test_replay_binds_source_revision():
    a = contract()
    b = ReplayContract(a.schema_version, a.project_id, "different", a.runtime_id,
                       a.runtime_version, a.fixed_tick_hz, a.seed, a.frames)
    assert a.digest() != b.digest()

def test_rejects_duplicate_ticks():
    bad = ReplayContract("1", "p", "sha", "runtime", "1", 60, 0,
                         (InputFrame(0), InputFrame(0)))
    with pytest.raises(ValueError, match="unique"):
        bad.validate()
