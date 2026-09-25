from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class FailureDescriptor:
    project_id: str
    source_revision: str
    category: str
    room: str
    summary: str
    replay_bundle_digest: str

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def failure_id(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()
