from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class RuntimeEvent:
    tick: int
    kind: str
    subject: str
    payload_digest: str = ""

@dataclass(frozen=True)
class StateCheckpoint:
    tick: int
    state_digest: str

@dataclass(frozen=True)
class RuntimeTrace:
    replay_digest: str
    events: tuple[RuntimeEvent, ...] = ()
    checkpoints: tuple[StateCheckpoint, ...] = ()

    def validate(self) -> None:
        event_ticks = [e.tick for e in self.events]
        checkpoint_ticks = [c.tick for c in self.checkpoints]
        if event_ticks != sorted(event_ticks):
            raise ValueError("events must be tick ordered")
        if checkpoint_ticks != sorted(checkpoint_ticks):
            raise ValueError("checkpoints must be tick ordered")

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()
