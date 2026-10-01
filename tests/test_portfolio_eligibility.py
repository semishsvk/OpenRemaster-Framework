import pytest
from openremaster.evidence import EvidenceGraph, EvidenceKey, EvidenceNode
from openremaster.portfolio import ProjectCheckpoint, evaluate_task_eligibility

TASK={"id":"T1","depends_on":["D1"]}

def cp(state="CANDIDATE", attestations=()):
    return ProjectCheckpoint("p","cp","o/r","main","abc",None,"snap",(),state,tuple(attestations),(),"next")

def test_dependency_blocks_before_other_gates():
    p={"local_state":"UNKNOWN"}
    assert evaluate_task_eligibility(TASK,p,set()).state == "BLOCKED_DEPENDENCY"

def test_unknown_local_blocks_execution():
    p={"local_state":"UNKNOWN"}
    assert evaluate_task_eligibility(TASK,p,{"D1"}).state == "BLOCKED_LOCAL"

def test_candidate_is_work_only():
    p={"local_state":"CAPTURED"}
    assert evaluate_task_eligibility(TASK,p,{"D1"},cp(),EvidenceGraph()).state == "READY_FOR_WORK"

def test_verified_is_ready_only_with_attestation():
    key=EvidenceKey("p","rev","input","tool","1","check")
    graph=EvidenceGraph([EvidenceNode(key,"pass")])
    result=evaluate_task_eligibility(TASK,{"local_state":"CAPTURED"},{"D1"},cp("VERIFIED",(key.stable_id(),)),graph)
    assert result.state == "READY"

def test_missing_verified_evidence_blocks():
    result=evaluate_task_eligibility(TASK,{"local_state":"CAPTURED"},{"D1"},cp("VERIFIED",("missing",)),EvidenceGraph())
    assert result.state == "BLOCKED_EVIDENCE"
