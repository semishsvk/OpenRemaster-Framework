from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from .replay import ReplayContract
from .trace import RuntimeTrace

@dataclass(frozen=True)
class ArtifactRef:
    role: str
    digest: str
    locator: str = ""

@dataclass(frozen=True)
class ReplayEvidenceBundle:
    schema_version: str
    replay: ReplayContract
    trace: RuntimeTrace
    artifacts: tuple[ArtifactRef, ...] = ()

    def validate(self) -> None:
        if self.schema_version != "1":
            raise ValueError("unsupported bundle schema")
        self.replay.validate()
        self.trace.validate()
        if self.trace.replay_digest != self.replay.digest():
            raise ValueError("trace is not bound to replay")
        roles = [a.role for a in self.artifacts]
        if roles != sorted(roles):
            raise ValueError("artifacts must be role sorted")
        if len(roles) != len(set(roles)):
            raise ValueError("artifact roles must be unique")
        for artifact in self.artifacts:
            if len(artifact.digest) != 64:
                raise ValueError("artifact digest must be sha256 hex")

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()
