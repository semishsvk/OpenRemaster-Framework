from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class GoldenState:
    state_id: str
    label: str

@dataclass(frozen=True)
class GoldenRoom:
    room_id: str
    states: tuple[GoldenState, ...] = ()
    asset_ids: tuple[str, ...] = ()

    def validate(self) -> None:
        state_ids = [s.state_id for s in self.states]
        if state_ids != sorted(state_ids) or len(state_ids) != len(set(state_ids)):
            raise ValueError("room states must be unique and sorted")
        if self.asset_ids != tuple(sorted(set(self.asset_ids))):
            raise ValueError("asset ids must be unique and sorted")

@dataclass(frozen=True)
class GoldenInventory:
    schema_version: str
    project_id: str
    source_revision: str
    rooms: tuple[GoldenRoom, ...]

    def validate(self) -> None:
        if self.schema_version != "1":
            raise ValueError("unsupported golden inventory schema")
        room_ids = [r.room_id for r in self.rooms]
        if room_ids != sorted(room_ids) or len(room_ids) != len(set(room_ids)):
            raise ValueError("rooms must be unique and sorted")
        for room in self.rooms:
            room.validate()

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()
