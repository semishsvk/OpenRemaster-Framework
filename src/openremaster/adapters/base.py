from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class ProjectSnapshot:
    project_id: str
    revision: str
    metadata: dict[str, str]

class ReadOnlyAdapter(ABC):
    """Observation-only boundary. No mutation API is exposed."""
    @abstractmethod
    def snapshot(self) -> ProjectSnapshot:
        raise NotImplementedError
