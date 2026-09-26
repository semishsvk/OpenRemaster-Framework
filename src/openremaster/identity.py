from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json


def _required(value: str, field: str) -> None:
    if not value.strip():
        raise ValueError(f"{field} is required")


def _sha256(value: str, field: str) -> None:
    if len(value) != 64:
        raise ValueError(f"{field} must be sha256 hex")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"{field} must be sha256 hex") from exc


@dataclass(frozen=True)
class EvidenceIdentity:
    """Canonical Phase-2 identity binding for evidence and derived artifacts."""

    schema_version: str
    project_id: str
    corpus_id: str
    artifact_id: str
    room_id: str
    state_id: str
    run_id: str
    source_revision: str
    dependency_digest: str

    def validate(self) -> None:
        if self.schema_version != "2":
            raise ValueError("unsupported evidence identity schema")
        for field in (
            "project_id", "corpus_id", "artifact_id", "room_id",
            "state_id", "run_id", "source_revision",
        ):
            _required(getattr(self, field), field)
        _sha256(self.dependency_digest, "dependency_digest")

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def digest(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def require_same_context(self, other: "EvidenceIdentity") -> None:
        """Fail closed when evidence from different contexts is combined."""
        self.validate()
        other.validate()
        fields = (
            "project_id", "corpus_id", "room_id", "state_id",
            "run_id", "source_revision", "dependency_digest",
        )
        mismatches = tuple(field for field in fields if getattr(self, field) != getattr(other, field))
        if mismatches:
            raise ValueError("evidence identity mismatch: " + ",".join(mismatches))
