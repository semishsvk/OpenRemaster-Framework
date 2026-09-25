from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Iterable

VALID_STATUSES = {"pass", "fail", "unknown"}
VALID_DEPENDENCY_TYPES = {"input", "derived", "runtime", "coverage"}

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
class EvidenceDependency:
    evidence_id: str
    kind: str = "derived"

    def validate(self) -> None:
        if self.kind not in VALID_DEPENDENCY_TYPES:
            raise ValueError("invalid dependency type")

@dataclass(frozen=True)
class EvidenceNode:
    key: EvidenceKey
    status: str
    dependencies: tuple[EvidenceDependency, ...] = ()

    def validate(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError("invalid evidence status")
        for dependency in self.dependencies:
            dependency.validate()

class EvidenceGraph:
    def __init__(self, nodes: Iterable[EvidenceNode] = ()) -> None:
        self._nodes: dict[str, EvidenceNode] = {}
        for node in nodes:
            self.add(node)

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
                if node_id not in invalid and any(d.evidence_id in invalid for d in node.dependencies):
                    invalid.add(node_id)
                    changed = True
        return invalid

    def to_json(self) -> str:
        records = []
        for node_id in sorted(self._nodes):
            node = self._nodes[node_id]
            records.append({
                "id": node_id,
                "key": asdict(node.key),
                "status": node.status,
                "dependencies": [asdict(d) for d in node.dependencies],
            })
        return json.dumps({"schema_version": "1", "nodes": records}, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, payload: str) -> "EvidenceGraph":
        raw = json.loads(payload)
        if raw.get("schema_version") != "1":
            raise ValueError("unsupported evidence schema")
        graph = cls()
        for record in raw.get("nodes", []):
            node = EvidenceNode(
                key=EvidenceKey(**record["key"]),
                status=record["status"],
                dependencies=tuple(EvidenceDependency(**d) for d in record.get("dependencies", [])),
            )
            if node.key.stable_id() != record["id"]:
                raise ValueError("evidence id mismatch")
            graph.add(node)
        return graph
