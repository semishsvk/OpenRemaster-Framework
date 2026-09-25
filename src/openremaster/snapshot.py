from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json

@dataclass(frozen=True)
class SourceSnapshot:
    project_id: str
    repository: str
    revision: str
    manifest_digest: str

    def digest(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode()).hexdigest()
