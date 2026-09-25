from __future__ import annotations
from dataclasses import dataclass
from .bundle import ReplayEvidenceBundle
from .golden import GoldenInventory
from .golden_links import GoldenEvidenceLink
from .visual import VisualCaptureContract

@dataclass(frozen=True)
class InvariantResult:
    valid: bool
    errors: tuple[str, ...]

def validate_cross_component(
    inventory: GoldenInventory,
    link: GoldenEvidenceLink,
    replay_bundle: ReplayEvidenceBundle | None = None,
    visual_contract: VisualCaptureContract | None = None,
) -> InvariantResult:
    errors: list[str] = []
    inventory.validate()
    known = {(r.room_id, s.state_id) for r in inventory.rooms for s in r.states}
    if (link.room_id, link.state_id) not in known:
        errors.append("golden link targets unknown room/state")
    try:
        link.validate()
    except ValueError as exc:
        errors.append(str(exc))
    if replay_bundle is not None:
        try:
            replay_bundle.validate()
            if replay_bundle.replay.project_id != inventory.project_id:
                errors.append("replay project mismatch")
            if replay_bundle.replay.source_revision != inventory.source_revision:
                errors.append("replay source revision mismatch")
            if link.replay_bundle_digest and replay_bundle.digest() != link.replay_bundle_digest:
                errors.append("replay bundle digest mismatch")
        except ValueError as exc:
            errors.append(str(exc))
    if visual_contract is not None:
        try:
            visual_contract.validate()
            if visual_contract.project_id != inventory.project_id:
                errors.append("visual project mismatch")
            if visual_contract.source_revision != inventory.source_revision:
                errors.append("visual source revision mismatch")
            if visual_contract.scene_id != link.room_id:
                errors.append("visual scene mismatch")
            if link.visual_baseline_digest and visual_contract.digest() != link.visual_baseline_digest:
                errors.append("visual contract digest mismatch")
        except ValueError as exc:
            errors.append(str(exc))
    return InvariantResult(not errors, tuple(errors))
