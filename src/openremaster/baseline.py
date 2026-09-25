from __future__ import annotations
from dataclasses import dataclass
from .evidence import EvidenceGraph, EvidenceKey, EvidenceNode
from .snapshot import SourceSnapshot

@dataclass(frozen=True)
class BaselineResult:
    snapshot: SourceSnapshot
    evidence_id: str

def register_source_baseline(graph: EvidenceGraph, snapshot: SourceSnapshot, tool_version: str) -> BaselineResult:
    key = EvidenceKey(
        project_id=snapshot.project_id,
        source_revision=snapshot.revision,
        input_digest=snapshot.manifest_digest,
        tool_id="openremaster.baseline",
        tool_version=tool_version,
        check_id="source-revision-observed",
    )
    evidence_id = graph.add(EvidenceNode(key, "pass"))
    return BaselineResult(snapshot, evidence_id)
