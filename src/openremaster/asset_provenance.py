from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

VALID_KINDS = frozenset({"source","decoded","transformed","runtime","entity"})
VALID_RELATIONS = frozenset({"extracted-from","decoded-from","transformed-from","built-from","used-by"})

@dataclass(frozen=True)
class AssetNode:
    asset_id: str
    kind: str
    digest: str
    locator: str = ""

    def validate(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError("invalid asset kind")
        if len(self.digest) != 64:
            raise ValueError("asset digest must be sha256 hex")

@dataclass(frozen=True)
class AssetEdge:
    source_id: str
    target_id: str
    relation: str
    tool_id: str = ""
    tool_version: str = ""

    def validate(self) -> None:
        if self.relation not in VALID_RELATIONS:
            raise ValueError("invalid provenance relation")

class AssetProvenanceGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, AssetNode] = {}
        self.edges: list[AssetEdge] = []

    def add_node(self, node: AssetNode) -> None:
        node.validate()
        existing = self.nodes.get(node.asset_id)
        if existing is not None and existing != node:
            raise ValueError("asset id collision")
        self.nodes[node.asset_id] = node

    def add_edge(self, edge: AssetEdge) -> None:
        edge.validate()
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError("edge endpoint missing")
        self.edges.append(edge)

    def ancestors(self, asset_id: str) -> tuple[str, ...]:
        if asset_id not in self.nodes:
            raise KeyError(asset_id)
        reverse: dict[str, set[str]] = {}
        for edge in self.edges:
            reverse.setdefault(edge.target_id, set()).add(edge.source_id)
        seen: set[str] = set()
        stack = list(reverse.get(asset_id, ()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(reverse.get(current, ()))
        return tuple(sorted(seen))

    def descendants(self, asset_id: str) -> tuple[str, ...]:
        if asset_id not in self.nodes:
            raise KeyError(asset_id)
        forward: dict[str, set[str]] = {}
        for edge in self.edges:
            forward.setdefault(edge.source_id, set()).add(edge.target_id)
        seen: set[str] = set()
        stack = list(forward.get(asset_id, ()))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(forward.get(current, ()))
        return tuple(sorted(seen))

    def canonical_json(self) -> str:
        payload = {
            "schema_version": "1",
            "nodes": [asdict(self.nodes[k]) for k in sorted(self.nodes)],
            "edges": [asdict(e) for e in sorted(self.edges, key=lambda e: (e.source_id,e.target_id,e.relation,e.tool_id,e.tool_version))],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()
