from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .base import ProjectSnapshot, ReadOnlyAdapter

class RevisionReader(Protocol):
    def resolve_revision(self, repository: str, ref: str) -> str: ...

@dataclass(frozen=True)
class GitHubProjectSpec:
    project_id: str
    repository: str
    ref: str
    role: str

class GitHubReadOnlyAdapter(ReadOnlyAdapter):
    """Adapter over an injected read-only revision reader."""
    def __init__(self, spec: GitHubProjectSpec, reader: RevisionReader) -> None:
        self.spec = spec
        self.reader = reader

    def snapshot(self) -> ProjectSnapshot:
        revision = self.reader.resolve_revision(self.spec.repository, self.spec.ref)
        return ProjectSnapshot(self.spec.project_id, revision, {
            "mode": "read-only",
            "role": self.spec.role,
            "repository": self.spec.repository,
            "ref": self.spec.ref,
        })
