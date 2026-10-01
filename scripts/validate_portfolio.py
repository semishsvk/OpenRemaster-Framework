from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_REMOTE = {"ACTIVE_PHASE2","CHECKPOINT_EXISTS","BOOTSTRAP","REMOTE_EMPTY","REMOTE_MISSING"}

def load_json(rel: str):
    with (ROOT / rel).open("r", encoding="utf-8") as f:
        return json.load(f)

def validate_portfolio() -> list[str]:
    errors: list[str] = []
    registry = load_json("portfolio/registry.json")
    tasks = load_json("portfolio/tasks.json")
    projects = registry.get("projects", [])
    ids = [p.get("id") for p in projects]
    if len(ids) != len(set(ids)):
        errors.append("duplicate project id")
    known = set(ids)
    for p in projects:
        state = p.get("remote_state")
        if state not in ALLOWED_REMOTE:
            errors.append(f"{p.get('id')}: invalid remote_state {state}")
        if state in {"REMOTE_EMPTY","REMOTE_MISSING"} and p.get("remote_checkpoint") is not None:
            errors.append(f"{p.get('id')}: empty/missing remote cannot have checkpoint")
        if p.get("local_state") == "UNKNOWN" and p.get("next_gate") not in {
            "LOCAL_STATE_REQUIRED","LOCAL_DIFF","LOCAL_DIFF_AND_FIDELITY_RECONCILIATION","PORTFOLIO_CONSOLIDATION"
        }:
            errors.append(f"{p.get('id')}: unknown local state has unsafe next gate")
    task_ids = [t.get("id") for t in tasks.get("tasks", [])]
    if len(task_ids) != len(set(task_ids)):
        errors.append("duplicate task id")
    task_set = set(task_ids)
    for t in tasks.get("tasks", []):
        if t.get("project") not in known:
            errors.append(f"{t.get('id')}: unknown project {t.get('project')}")
        for dep in t.get("depends_on", []):
            if dep not in task_set:
                errors.append(f"{t.get('id')}: unknown dependency {dep}")
    return errors

if __name__ == "__main__":
    errs = validate_portfolio()
    if errs:
        raise SystemExit("\n".join(errs))
    print("PORTFOLIO VALID")
