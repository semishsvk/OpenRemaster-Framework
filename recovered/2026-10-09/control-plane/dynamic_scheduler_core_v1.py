"""Pure fail-closed dynamic lane planner. No process execution or lease mutation."""
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class Task:
    project: str
    task_id: str
    priority: int
    capabilities: Tuple[str,...]
    scope_approved: bool
    hashes_verified: bool
    dependencies_ready: bool
    admission_valid: bool
    lease_valid: bool
    writer_available: bool
    heavy: bool = True

@dataclass(frozen=True)
class Worker:
    worker_id: str
    capabilities: Tuple[str,...]
    commissioned: bool
    available: bool

def plan(tasks, workers, running=(), max_workers=3, max_heavy=3):
    """Return proposed assignments, never launch. Running includes ALL known heavy jobs."""
    if not isinstance(running,(tuple,list)) or any(not isinstance(x,dict) for x in running):
        return {"status":"BLOCKED","reason":"UNKNOWN_RUNNING_CAPACITY","assignments":[]}
    if any("project" not in x or "worker_id" not in x or "heavy" not in x for x in running):
        return {"status":"BLOCKED","reason":"INCOMPLETE_RUNNING_ACCOUNTING","assignments":[]}
    if len(running)>max_workers or sum(bool(x["heavy"]) for x in running)>max_heavy:
        return {"status":"BLOCKED","reason":"OVER_CAPACITY","assignments":[]}
    used_projects={x["project"] for x in running}
    used_workers={x["worker_id"] for x in running}
    slots=max(0,max_workers-len(running))
    heavy_slots=max(0,max_heavy-sum(bool(x["heavy"]) for x in running))
    assignments=[];rejections=[]
    for t in sorted(tasks,key=lambda x:(-x.priority,x.project,x.task_id)):
        if t.project in ("OpenAzrael-Retail","OpenAzrael-Demo"):
            rejections.append((t.task_id,"PAUSED_OR_CLOSED"));continue
        if t.project in used_projects:
            rejections.append((t.task_id,"PROJECT_WIP"));continue
        checks=(("SCOPE",t.scope_approved),("HASH",t.hashes_verified),
                ("DEPENDENCY",t.dependencies_ready),("ADMISSION",t.admission_valid),
                ("LEASE",t.lease_valid),("SINGLE_WRITER",t.writer_available))
        bad=next((label for label,ok in checks if not ok),None)
        if bad:
            rejections.append((t.task_id,bad));continue
        if slots<=0 or (t.heavy and heavy_slots<=0):
            rejections.append((t.task_id,"CAPACITY"));continue
        w=next((w for w in sorted(workers,key=lambda w:w.worker_id)
                if w.commissioned and w.available and w.worker_id not in used_workers
                and set(t.capabilities).issubset(w.capabilities)),None)
        if not w:
            rejections.append((t.task_id,"NO_CAPABLE_FREE_WORKER"));continue
        assignments.append({"project":t.project,"task_id":t.task_id,"worker_id":w.worker_id,
                            "heavy":t.heavy,"status":"PROPOSED_ONLY"})
        used_projects.add(t.project);used_workers.add(w.worker_id)
        slots-=1;heavy_slots-=int(t.heavy)
    return {"status":"PLAN_ONLY","assignments":assignments,"rejections":rejections}
