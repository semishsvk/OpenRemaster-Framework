from __future__ import annotations
from dataclasses import asdict, dataclass
import json
from .cache import CacheDecision
from .evidence import EvidenceKey
from .reuse import PlannedCheck

@dataclass(frozen=True)
class ProvenanceRecord:
    suite_id: str
    decision: str
    reason: str
    project_id: str
    source_revision: str
    input_digest: str | None
    tool_id: str
    tool_version: str
    evidence_id: str | None

def build_provenance(
    check: PlannedCheck,
    project_id: str,
    source_revision: str,
    input_digest: str | None,
    tool_id: str,
    tool_version: str,
) -> ProvenanceRecord:
    evidence_id = None
    if input_digest is not None:
        key = EvidenceKey(project_id, source_revision, input_digest, tool_id, tool_version, check.suite_id)
        evidence_id = key.stable_id()
    return ProvenanceRecord(
        suite_id=check.suite_id,
        decision=check.decision.value,
        reason=check.reason,
        project_id=project_id,
        source_revision=source_revision,
        input_digest=input_digest,
        tool_id=tool_id,
        tool_version=tool_version,
        evidence_id=evidence_id,
    )

def provenance_json(records: tuple[ProvenanceRecord, ...]) -> str:
    return json.dumps(
        {"schema_version": "1", "records": [asdict(r) for r in records]},
        sort_keys=True, separators=(",", ":"),
    ) + "\n"
