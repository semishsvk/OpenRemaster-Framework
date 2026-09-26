from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .evidence import EvidenceGraph


class Freshness(str, Enum):
    CURRENT = "current"
    STALE = "stale"


@dataclass(frozen=True)
class EvidenceFreshness:
    evidence_id: str
    freshness: Freshness
    stale_roots: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if self.stale_roots != tuple(sorted(set(self.stale_roots))):
            raise ValueError("stale roots must be unique and sorted")
        if self.freshness is Freshness.CURRENT and self.stale_roots:
            raise ValueError("current evidence cannot have stale roots")
        if self.freshness is Freshness.STALE and not self.stale_roots:
            raise ValueError("stale evidence requires stale roots")


class ProvenanceFreshness:
    """Deterministic, non-mutating freshness projection over an EvidenceGraph."""

    def __init__(self, graph: EvidenceGraph) -> None:
        graph.validate_references()
        self._graph = graph

    def evaluate(self, changed_ids: set[str]) -> tuple[EvidenceFreshness, ...]:
        missing = sorted(changed_ids.difference(self._graph.ids()))
        if missing:
            raise ValueError("unknown changed evidence: " + ",".join(missing))

        roots_by_node: dict[str, set[str]] = {node_id: set() for node_id in self._graph.ids()}
        for root in sorted(changed_ids):
            roots_by_node[root].add(root)

        changed = True
        while changed:
            changed = False
            for node_id in self._graph.ids():
                node = self._graph.get(node_id)
                propagated = set(roots_by_node[node_id])
                for dependency in node.dependencies:
                    propagated.update(roots_by_node[dependency.evidence_id])
                if propagated != roots_by_node[node_id]:
                    roots_by_node[node_id] = propagated
                    changed = True

        result = tuple(
            EvidenceFreshness(
                node_id,
                Freshness.STALE if roots_by_node[node_id] else Freshness.CURRENT,
                tuple(sorted(roots_by_node[node_id])),
            )
            for node_id in self._graph.ids()
        )
        for item in result:
            item.validate()
        return result
