from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class InputFrame:
    tick: int
    actions: tuple[str, ...] = ()
    axes: tuple[tuple[str, float], ...] = ()

    def validate(self) -> None:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        if tuple(sorted(self.actions)) != self.actions:
            raise ValueError("actions must be sorted")
        if tuple(sorted(self.axes)) != self.axes:
            raise ValueError("axes must be sorted")

@dataclass(frozen=True)
class ReplayContract:
    schema_version: str
    project_id: str
    source_revision: str
    runtime_id: str
    runtime_version: str
    fixed_tick_hz: int
    seed: int
    frames: tuple[InputFrame, ...]

    def validate(self) -> None:
        if self.schema_version != "1":
            raise ValueError("unsupported replay schema")
        if self.fixed_tick_hz <= 0:
            raise ValueError("fixed_tick_hz must be positive")
        ticks = [f.tick for f in self.frames]
        if ticks != sorted(ticks) or len(ticks) != len(set(ticks)):
            raise ValueError("ticks must be unique and sorted")
        for frame in self.frames:
            frame.validate()

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()
