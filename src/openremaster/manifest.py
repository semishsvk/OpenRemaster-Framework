from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class SourceRef:
    kind: str
    locator: str
    digest: str | None = None

@dataclass(frozen=True)
class ProjectManifest:
    schema_version: str
    project_id: str
    project_name: str
    adapter: str
    sources: tuple[SourceRef, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version != "1":
            raise ValueError("unsupported manifest schema")
        if not self.project_id.strip():
            raise ValueError("project_id is required")
        if not self.adapter.strip():
            raise ValueError("adapter is required")
