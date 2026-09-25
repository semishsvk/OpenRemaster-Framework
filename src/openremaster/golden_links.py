from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class GoldenEvidenceLink:
    room_id: str
    state_id: str
    replay_bundle_digest: str = ""
    visual_baseline_digest: str = ""
    asset_graph_digest: str = ""

    def validate(self) -> None:
        for value in (self.replay_bundle_digest, self.visual_baseline_digest, self.asset_graph_digest):
            if value and len(value) != 64:
                raise ValueError("evidence link digest must be sha256 hex")
