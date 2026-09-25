from openremaster.replay_compare import compare_traces
from openremaster.trace import RuntimeEvent, RuntimeTrace, StateCheckpoint

def trace(state="world-a", subject="door"):
    return RuntimeTrace(
        "replay",
        (RuntimeEvent(10, "interaction", subject, "payload"),),
        (StateCheckpoint(10, state),),
    )

def test_identical_traces_are_deterministic():
    assert compare_traces(trace(), trace()).deterministic

def test_state_divergence_is_detected():
    result = compare_traces(trace(), trace(state="world-b"))
    assert not result.deterministic
    assert result.first_checkpoint_mismatch == 0

def test_event_divergence_is_detected():
    result = compare_traces(trace(), trace(subject="tongs"))
    assert not result.deterministic
    assert result.first_event_mismatch == 0
