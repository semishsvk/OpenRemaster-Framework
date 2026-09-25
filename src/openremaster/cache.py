from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .evidence import EvidenceKey, EvidenceNode

class CacheDecision(str, Enum):
    REUSE = "reuse"
    RERUN = "rerun"

@dataclass(frozen=True)
class CacheRequest:
    key: EvidenceKey
    require_pass: bool = True

@dataclass(frozen=True)
class CacheResult:
    decision: CacheDecision
    evidence_id: str | None
    reason: str

class EvidenceCache:
    """Deterministic in-memory index over immutable evidence identity."""
    def __init__(self, nodes: tuple[EvidenceNode, ...] = ()) -> None:
        self._by_id = {node.key.stable_id(): node for node in nodes}

    def put(self, node: EvidenceNode) -> str:
        node.validate()
        evidence_id = node.key.stable_id()
        self._by_id[evidence_id] = node
        return evidence_id

    def decide(self, request: CacheRequest) -> CacheResult:
        evidence_id = request.key.stable_id()
        node = self._by_id.get(evidence_id)
        if node is None:
            return CacheResult(CacheDecision.RERUN, None, "identity miss")
        if request.require_pass and node.status != "pass":
            return CacheResult(CacheDecision.RERUN, evidence_id, f"cached status is {node.status}")
        return CacheResult(CacheDecision.REUSE, evidence_id, "exact immutable identity match")
