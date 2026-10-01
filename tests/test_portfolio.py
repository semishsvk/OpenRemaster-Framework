import pytest
from openremaster.evidence import EvidenceGraph, EvidenceKey, EvidenceNode
from openremaster.portfolio import ProjectCheckpoint, validate_task_dag

def test_verified_checkpoint_requires_real_evidence_attestation():
    key = EvidenceKey("p","rev","input","tool","1","check")
    graph = EvidenceGraph([EvidenceNode(key, "pass")])
    cp = ProjectCheckpoint("p","cp","o/r","main","abc",None,"snap",(), "VERIFIED",(key.stable_id(),),(),"next")
    cp.validate(graph)
    assert len(cp.occurrence_id()) == 64

def test_verified_checkpoint_rejects_missing_attestation():
    cp = ProjectCheckpoint("p","cp","o/r","main","abc",None,"snap",(), "VERIFIED",("missing",),(),"next")
    with pytest.raises(ValueError, match="missing evidence"):
        cp.validate(EvidenceGraph())

def test_candidate_requires_local_snapshot():
    cp = ProjectCheckpoint("p","cp","o/r","main","abc",None,None,(), "CANDIDATE",(),(),"next")
    with pytest.raises(ValueError, match="local snapshot"):
        cp.validate()

def test_task_dag_rejects_cycle():
    with pytest.raises(ValueError, match="cycle"):
        validate_task_dag([{"id":"A","depends_on":["B"]},{"id":"B","depends_on":["A"]}])
