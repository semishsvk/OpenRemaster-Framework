import pytest
from openremaster.replay import InputFrame, ReplayContract
from openremaster.replay_slice import slice_replay

def replay():
    return ReplayContract(
        "1","p","sha","runtime","1",60,9,
        tuple(InputFrame(i, (f"a{i}",), ()) for i in range(10))
    )

def test_slice_rebases_ticks_and_preserves_identity_context():
    s = slice_replay(replay(), 4, 7, "checkpoint-state")
    assert [f.tick for f in s.replay.frames] == [0,1,2,3]
    assert s.replay.source_revision == "sha"
    assert s.source_replay_digest == replay().digest()
    assert s.initial_state_digest == "checkpoint-state"

def test_invalid_bounds_rejected():
    with pytest.raises(ValueError, match="bounds"):
        slice_replay(replay(), 5, 4, "state")
