from __future__ import annotations
from dataclasses import dataclass
from .replay import ReplayContract
from .replay_slice import ReplaySlice, slice_replay
from .trace import RuntimeTrace

@dataclass(frozen=True)
class FailureWindow:
    failure_tick: int
    checkpoint_tick: int
    checkpoint_digest: str
    replay_slice: ReplaySlice

def nearest_checkpoint(trace: RuntimeTrace, failure_tick: int) -> tuple[int, str]:
    trace.validate()
    eligible = [c for c in trace.checkpoints if c.tick <= failure_tick]
    if not eligible:
        raise ValueError("no checkpoint at or before failure")
    checkpoint = eligible[-1]
    return checkpoint.tick, checkpoint.state_digest

def build_failure_window(
    replay: ReplayContract,
    trace: RuntimeTrace,
    failure_tick: int,
) -> FailureWindow:
    if trace.replay_digest != replay.digest():
        raise ValueError("trace is not bound to replay")
    checkpoint_tick, checkpoint_digest = nearest_checkpoint(trace, failure_tick)
    replay_slice = slice_replay(replay, checkpoint_tick, failure_tick, checkpoint_digest)
    return FailureWindow(failure_tick, checkpoint_tick, checkpoint_digest, replay_slice)
