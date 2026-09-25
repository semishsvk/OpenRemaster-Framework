from __future__ import annotations
from dataclasses import dataclass
from .asset_provenance import AssetProvenanceGraph

@dataclass(frozen=True)
class AssetImpact:
    changed: tuple[str, ...]
    affected: tuple[str, ...]

def analyze_asset_impact(graph: AssetProvenanceGraph, changed: set[str]) -> AssetImpact:
    affected = set(changed)
    for asset_id in changed:
        affected.update(graph.descendants(asset_id))
    return AssetImpact(tuple(sorted(changed)), tuple(sorted(affected)))
