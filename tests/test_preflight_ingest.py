import copy
import pytest
from openremaster.portfolio import ingest_preflight, planning_projection, ProjectCheckpoint

BASE={
 "schema_version":"1.0","project_id":"p","captured_at":"2026-10-01T00:00:00+00:00",
 "git":{"repo_path":"/x","branch":"main","head":"abc","upstream":None,"remotes":[]},
 "worktrees":[],"changes":{"staged":[],"unstaged":[],"untracked":[]},"inputs":[],
 "safe_to_plan_sync":True
}

def test_preflight_occurrence_is_deterministic():
    a=ingest_preflight(copy.deepcopy(BASE),"p")
    b=ingest_preflight(copy.deepcopy(BASE),"p")
    assert a.occurrence_id==b.occurrence_id

def test_preflight_rejects_false_safe_claim():
    p=copy.deepcopy(BASE); p["changes"]["untracked"]=["wip.py"]
    with pytest.raises(ValueError,match="unsafe preflight"):
        ingest_preflight(p)

def test_projection_uses_occurrence_as_captured_local_state():
    occ=ingest_preflight(copy.deepcopy(BASE))
    task={"id":"T","project":"p","depends_on":[]}
    project={"id":"p","local_state":"UNKNOWN"}
    cp=ProjectCheckpoint("p","cp","o/r","main","abc",None,"snap",(),"CANDIDATE",(),(),"next")
    result=planning_projection([task],[project],{"p":occ},{"p":cp})
    assert result[0].state=="READY_FOR_WORK"

def test_projection_without_occurrence_stays_blocked_local():
    task={"id":"T","project":"p","depends_on":[]}
    project={"id":"p","local_state":"UNKNOWN"}
    result=planning_projection([task],[project],{}, {})
    assert result[0].state=="BLOCKED_LOCAL"
