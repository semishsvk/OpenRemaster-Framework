from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from .evidence import EvidenceDependency, EvidenceKey, EvidenceNode

@dataclass(frozen=True)
class StoredEvidence:
    evidence_id: str
    node: EvidenceNode

class JsonEvidenceStore:
    """Content-addressed local artifact store. No project-tree writes are implied."""
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, evidence_id: str) -> Path:
        return self.root / evidence_id[:2] / f"{evidence_id}.json"

    def put(self, node: EvidenceNode) -> StoredEvidence:
        node.validate()
        evidence_id = node.key.stable_id()
        payload = {
            "schema_version": "1",
            "id": evidence_id,
            "key": asdict(node.key),
            "status": node.status,
            "dependencies": [asdict(d) for d in node.dependencies],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        path = self._path(evidence_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(encoded, encoding="utf-8")
        return StoredEvidence(evidence_id, node)

    def get(self, evidence_id: str) -> StoredEvidence:
        payload = json.loads(self._path(evidence_id).read_text(encoding="utf-8"))
        node = EvidenceNode(
            key=EvidenceKey(**payload["key"]),
            status=payload["status"],
            dependencies=tuple(EvidenceDependency(**d) for d in payload.get("dependencies", [])),
        )
        if payload.get("schema_version") != "1":
            raise ValueError("unsupported store schema")
        if node.key.stable_id() != evidence_id or payload.get("id") != evidence_id:
            raise ValueError("stored evidence identity mismatch")
        return StoredEvidence(evidence_id, node)

    def artifact_digest(self, evidence_id: str) -> str:
        return sha256(self._path(evidence_id).read_bytes()).hexdigest()
