import copy
import json
import pytest
from openremaster.portfolio import (
    PreflightOccurrenceStore, ProjectCheckpoint, ingest_preflight, planning_report
)

BASE={
 "schema_version":"1.0","project_id":"p","captured_at":"2026-10-01T00:00:00+00:00",
 "git":{"repo_path":"/x","branch":"main","head":"abc","upstream":None,"remotes":[]},
 "worktrees":[],"changes":{"staged":[],"unstaged":[],"untracked":[]},"inputs":[],
 "safe_to_plan_sync":True
}

def test_occurrence_store_roundtrip_and_idempotent_put(tmp_path):
    occ=ingest_preflight(copy.deepcopy(BASE))
    store=PreflightOccurrenceStore(tmp_path)
    assert store.put(occ)==occ.occurrence_id
    assert store.put(occ)==occ.occurrence_id
    assert store.get(occ.occurrence_id)==occ

def test_occurrence_store_detects_tampering(tmp_path):
    occ=ingest_preflight(copy.deepcopy(BASE)); store=PreflightOccurrenceStore(tmp_path)
    store.put(occ)
    path=store._path(occ.occurrence_id)
    payload=json.loads(path.read_text()); payload["project_id"]="evil"
    path.write_text(json.dumps(payload),encoding="utf-8")
    with pytest.raises(ValueError):
        store.get(occ.occurrence_id)

def test_planning_report_counts_states():
    occ=ingest_preflight(copy.deepcopy(BASE))
    tasks=[
      {"id":"A","project":"p","depends_on":[],"action":"work"},
      {"id":"B","project":"q","depends_on":[],"action":"wait"},
    ]
    projects=[{"id":"p","local_state":"UNKNOWN"},{"id":"q","local_state":"UNKNOWN"}]
    cp=ProjectCheckpoint("p","cp","o/r","main","abc",None,"snap",(),"CANDIDATE",(),(),"next")
    report=planning_report(tasks,projects,{"p":occ},{"p":cp})
    assert report["counts"]["READY_FOR_WORK"]==1
    assert report["counts"]["BLOCKED_LOCAL"]==1
    assert [x["task_id"] for x in report["tasks"]]==["A","B"]
