from __future__ import annotations
from dataclasses import dataclass
from .visual import VisualArtifact, VisualCaptureContract

@dataclass(frozen=True)
class VisualBaseline:
    name: str
    contract: VisualCaptureContract
    artifact: VisualArtifact

    def validate(self) -> None:
        self.contract.validate()
        self.artifact.validate()
        if self.contract.digest() != self.artifact.contract_digest:
            raise ValueError("artifact is not bound to capture contract")
