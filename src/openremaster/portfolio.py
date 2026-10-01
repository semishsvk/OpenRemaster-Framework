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


ELIGIBILITY = {"READY", "READY_FOR_WORK", "BLOCKED_LOCAL", "BLOCKED_EVIDENCE", "BLOCKED_DEPENDENCY"}

@dataclass(frozen=True)
class TaskEligibility:
    task_id: str
    state: str
    reasons: tuple[str, ...] = ()

def evaluate_task_eligibility(
    task: dict,
    project: dict,
    completed_tasks: set[str],
    checkpoint: ProjectCheckpoint | None = None,
    evidence: EvidenceGraph | None = None,
) -> TaskEligibility:
    reasons: list[str] = []
    missing_deps = sorted(set(task.get("depends_on", ())) - completed_tasks)
    if missing_deps:
        return TaskEligibility(task["id"], "BLOCKED_DEPENDENCY", tuple(missing_deps))

    if project.get("local_state") == "UNKNOWN":
        return TaskEligibility(task["id"], "BLOCKED_LOCAL", ("local_state_unknown",))

    if checkpoint is None:
        return TaskEligibility(task["id"], "BLOCKED_EVIDENCE", ("checkpoint_missing",))

    try:
        checkpoint.validate(evidence)
    except ValueError as exc:
        return TaskEligibility(task["id"], "BLOCKED_EVIDENCE", (str(exc),))

    if checkpoint.validation_state in {"UNKNOWN", "BLOCKED", "FALSIFIED"}:
        return TaskEligibility(task["id"], "BLOCKED_EVIDENCE", (checkpoint.validation_state.lower(),))

    # Candidate checkpoints may be handed to Work for bounded implementation;
    # only independently attested VERIFIED checkpoints are directly executable.
    if checkpoint.validation_state == "CANDIDATE":
        return TaskEligibility(task["id"], "READY_FOR_WORK")
    return TaskEligibility(task["id"], "READY")


@dataclass(frozen=True)
class PreflightOccurrence:
    occurrence_id: str
    project_id: str
    payload: dict

def ingest_preflight(payload: dict, expected_project_id: str | None = None) -> PreflightOccurrence:
    required = {"schema_version","project_id","captured_at","git","worktrees","changes","inputs","safe_to_plan_sync"}
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError("missing preflight fields: " + ",".join(missing))
    if payload["schema_version"] != "1.0":
        raise ValueError("unsupported preflight schema")
    if expected_project_id is not None and payload["project_id"] != expected_project_id:
        raise ValueError("preflight project mismatch")
    git = payload["git"]
    for field in ("repo_path","branch","head","upstream","remotes"):
        if field not in git:
            raise ValueError(f"missing preflight git field: {field}")
    changes = payload["changes"]
    for field in ("staged","unstaged","untracked"):
        if field not in changes:
            raise ValueError(f"missing preflight changes field: {field}")
    if payload["safe_to_plan_sync"] and (
        not git["head"] or changes["staged"] or changes["unstaged"] or changes["untracked"]
    ):
        raise ValueError("unsafe preflight claims safe_to_plan_sync")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    oid = sha256(canonical.encode("utf-8")).hexdigest()
    return PreflightOccurrence(oid, payload["project_id"], payload)

def planning_projection(
    tasks: Iterable[dict],
    projects: Iterable[dict],
    preflights: dict[str, PreflightOccurrence],
    checkpoints: dict[str, ProjectCheckpoint],
    evidence: EvidenceGraph | None = None,
    completed_tasks: set[str] | None = None,
) -> tuple[TaskEligibility, ...]:
    completed = completed_tasks or set()
    project_map = {p["id"]: dict(p) for p in projects}
    out: list[TaskEligibility] = []
    for task in tasks:
        project = project_map[task["project"]]
        occurrence = preflights.get(task["project"])
        if occurrence is not None:
            project["local_state"] = "CAPTURED"
        out.append(evaluate_task_eligibility(
            task, project, completed, checkpoints.get(task["project"]), evidence
        ))
    return tuple(out)
