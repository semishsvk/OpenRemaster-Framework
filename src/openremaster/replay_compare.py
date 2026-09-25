from __future__ import annotations
from dataclasses import dataclass
from .trace import RuntimeTrace

@dataclass(frozen=True)
class ReplayComparison:
    deterministic: bool
    first_event_mismatch: int | None
    first_checkpoint_mismatch: int | None

def compare_traces(left: RuntimeTrace, right: RuntimeTrace) -> ReplayComparison:
    left.validate()
    right.validate()
    event_mismatch = None
    checkpoint_mismatch = None

    max_events = max(len(left.events), len(right.events))
    for i in range(max_events):
        if i >= len(left.events) or i >= len(right.events) or left.events[i] != right.events[i]:
            event_mismatch = i
            break

    max_checkpoints = max(len(left.checkpoints), len(right.checkpoints))
    for i in range(max_checkpoints):
        if i >= len(left.checkpoints) or i >= len(right.checkpoints) or left.checkpoints[i] != right.checkpoints[i]:
            checkpoint_mismatch = i
            break

    same_replay = left.replay_digest == right.replay_digest
    return ReplayComparison(
        deterministic=same_replay and event_mismatch is None and checkpoint_mismatch is None,
        first_event_mismatch=event_mismatch,
        first_checkpoint_mismatch=checkpoint_mismatch,
    )
