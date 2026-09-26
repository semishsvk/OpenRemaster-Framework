from __future__ import annotations
from dataclasses import dataclass, replace
from .replay import ReplayContract

@dataclass(frozen=True)
class ReplaySlice:
    source_replay_digest: str
    start_tick: int
    end_tick: int
    initial_state_digest: str
    replay: ReplayContract

    def validate(self) -> None:
        if self.start_tick < 0 or self.end_tick < self.start_tick:
            raise ValueError("invalid replay slice bounds")
        if not self.initial_state_digest:
            raise ValueError("initial state digest is required")
        self.replay.validate()
        ticks = [f.tick for f in self.replay.frames]
        if ticks and (ticks[0] != 0 or ticks[-1] > self.end_tick - self.start_tick):
            raise ValueError("slice frames must be rebased to zero")

def slice_replay(
    replay: ReplayContract,
    start_tick: int,
    end_tick: int,
    initial_state_digest: str,
) -> ReplaySlice:
    replay.validate()
    if start_tick < 0 or end_tick < start_tick:
        raise ValueError("invalid replay slice bounds")
    frames = tuple(
        type(frame)(
            tick=frame.tick - start_tick,
            actions=frame.actions,
            axes=frame.axes,
        )
        for frame in replay.frames
        if start_tick <= frame.tick <= end_tick
    )
    sliced = replace(replay, frames=frames)
    result = ReplaySlice(replay.digest(), start_tick, end_tick, initial_state_digest, sliced)
    result.validate()
    return result
