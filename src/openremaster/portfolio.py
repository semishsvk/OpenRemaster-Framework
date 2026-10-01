from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Iterable

from .evidence import EvidenceGraph

VALID_CHECKPOINT_STATES = {"UNKNOWN", "CANDIDATE", "VERIFIED", "FALSIFIED", "BLOCKED"}

@dataclass(frozen=True)
class ProjectCheckpoint:
    project_id: str
    checkpoint_id: str
    repo: str | None
    branch: str | None
    head: str | None
    tree_identity: str | None
    local_snapshot: str | None
    corpus_refs: tuple[str, ...]
    validation_state: str
    attestations: tuple[str, ...]
    tasks: tuple[str, ...]
    next_action: str

    def validate(self, evidence: EvidenceGraph | None = None) -> None:
        if not self.project_id.strip() or not self.checkpoint_id.strip():
            raise ValueError("project_id and checkpoint_id are required")
        if self.validation_state not in VALID_CHECKPOINT_STATES:
            raise ValueError("invalid checkpoint validation state")
        if self.validation_state == "VERIFIED" and not self.attestations:
            raise ValueError("verified checkpoint requires attestations")
        if self.local_snapshot is None and self.validation_state in {"CANDIDATE", "VERIFIED"}:
            raise ValueError("candidate/verified checkpoint requires local snapshot")
        if evidence is not None:
            known = set(evidence.ids())
            missing = sorted(set(self.attestations) - known)
            if missing:
                raise ValueError("missing evidence attestations: " + ",".join(missing))

    def occurrence_id(self) -> str:
        self.validate()
        payload = {
            "project_id": self.project_id,
            "checkpoint_id": self.checkpoint_id,
            "repo": self.repo,
            "branch": self.branch,
            "head": self.head,
            "tree_identity": self.tree_identity,
            "local_snapshot": self.local_snapshot,
            "corpus_refs": sorted(self.corpus_refs),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(encoded.encode("utf-8")).hexdigest()

def validate_task_dag(tasks: Iterable[dict]) -> None:
    records = {t["id"]: t for t in tasks}
    if len(records) != len(list(tasks)):
        raise ValueError("duplicate task id")
    for task in records.values():
        for dep in task.get("depends_on", []):
            if dep not in records:
                raise ValueError(f"unknown dependency: {task['id']} -> {dep}")
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"task dependency cycle at {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dep in records[task_id].get("depends_on", []):
            visit(dep)
        visiting.remove(task_id)
        visited.add(task_id)
    for task_id in sorted(records):
        visit(task_id)
