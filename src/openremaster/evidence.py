from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Iterable

@dataclass(frozen=True)
class EvidenceKey:
    project_id: str
    source_revision: str
    input_digest: str
    tool_id: str
    tool_version: str
    check_id: str

    def stable_id(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return sha256(payload.encode()).hexdigest()

@dataclass(frozen=True)
class EvidenceNode:
    key: EvidenceKey
    status: str
    dependencies: tuple[str, ...] = ()

    def validate(self) -> None:
        if self.status not in {"pass", "fail", "unknown"}:
            raise ValueError("invalid evidence status")

class EvidenceGraph:
    def __init__(self, nodes: Iterable[EvidenceNode] = ()) -> None:
        self._nodes = {n.key.stable_id(): n for n in nodes}

    def add(self, node: EvidenceNode) -> str:
        node.validate()
        node_id = node.key.stable_id()
        self._nodes[node_id] = node
        return node_id

    def get(self, node_id: str) -> EvidenceNode:
        return self._nodes[node_id]

    def invalidated_by(self, changed_ids: set[str]) -> set[str]:
        invalid = set(changed_ids)
        changed = True
        while changed:
            changed = False
            for node_id, node in self._nodes.items():
                if node_id not in invalid and any(d in invalid for d in node.dependencies):
                    invalid.add(node_id)
                    changed = True
        return invalid
