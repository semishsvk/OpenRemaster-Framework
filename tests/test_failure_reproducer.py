import pytest
from openremaster.failure_reproducer import build_failure_window
from openremaster.replay import InputFrame, ReplayContract
from openremaster.trace import RuntimeTrace, StateCheckpoint

def replay():
    return ReplayContract(
        "1","openazrael","sha","godot","4",60,1,
        tuple(InputFrame(i) for i in range(21))
    )

def test_uses_nearest_prior_checkpoint():
    r = replay()
    trace = RuntimeTrace(
        r.digest(), (),
        (StateCheckpoint(0,"s0"),StateCheckpoint(10,"s10"),StateCheckpoint(20,"s20"))
    )
    window = build_failure_window(r, trace, 17)
    assert window.checkpoint_tick == 10
    assert window.checkpoint_digest == "s10"
    assert window.replay_slice.start_tick == 10
    assert window.replay_slice.end_tick == 17
    assert [f.tick for f in window.replay_slice.replay.frames] == list(range(8))

def test_no_prior_checkpoint_is_rejected():
    r = replay()
    trace = RuntimeTrace(r.digest(), (), (StateCheckpoint(10,"s10"),))
    with pytest.raises(ValueError, match="no checkpoint"):
        build_failure_window(r, trace, 5)

def test_wrong_trace_binding_is_rejected():
    r = replay()
    with pytest.raises(ValueError, match="not bound"):
        build_failure_window(r, RuntimeTrace("other"), 5)
