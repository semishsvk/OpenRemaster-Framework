from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from .freshness import EvidenceFreshness, Freshness
from .identity import EvidenceIdentity
from .lifecycle import EvidenceStage, LifecycleEvidence


@dataclass(frozen=True)
class EvidenceRecord:
    identity: EvidenceIdentity
    stage: EvidenceStage
    evidence_id: str
    freshness: EvidenceFreshness
    reason: str = ""

    def validate(self) -> None:
        lifecycle = LifecycleEvidence(self.identity, self.stage, self.evidence_id, self.reason)
        lifecycle.validate()
        self.freshness.validate()
        if self.freshness.evidence_id != self.evidence_id:
            raise ValueError("freshness evidence identity mismatch")


@dataclass(frozen=True)
class EvidenceReport:
    records: tuple[EvidenceRecord, ...]

    def validate(self) -> None:
        ids = [record.evidence_id for record in self.records]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("evidence report records must be unique and sorted")
        for record in self.records:
            record.validate()

    def canonical_json(self) -> str:
        self.validate()
        payload = {
            "schema_version": "2",
            "records": [
                {
                    "identity": asdict(record.identity),
                    "stage": record.stage.value,
                    "evidence_id": record.evidence_id,
                    "freshness": {
                        "evidence_id": record.freshness.evidence_id,
                        "freshness": record.freshness.freshness.value,
                        "stale_roots": list(record.freshness.stale_roots),
                    },
                    "reason": record.reason,
                }
                for record in self.records
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"

    def digest(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, payload: str) -> "EvidenceReport":
        raw = json.loads(payload)
        if raw.get("schema_version") != "2":
            raise ValueError("unsupported evidence report schema")
        records = []
        for item in raw.get("records", []):
            freshness = item["freshness"]
            record = EvidenceRecord(
                EvidenceIdentity(**item["identity"]),
                EvidenceStage(item["stage"]),
                item["evidence_id"],
                EvidenceFreshness(
                    freshness["evidence_id"],
                    Freshness(freshness["freshness"]),
                    tuple(freshness.get("stale_roots", ())),
                ),
                item.get("reason", ""),
            )
            records.append(record)
        report = cls(tuple(records))
        report.validate()
        return report


def build_evidence_report(
    lifecycle: tuple[LifecycleEvidence, ...],
    freshness: tuple[EvidenceFreshness, ...],
) -> EvidenceReport:
    freshness_by_id = {item.evidence_id: item for item in freshness}
    if len(freshness_by_id) != len(freshness):
        raise ValueError("duplicate freshness evidence id")
    lifecycle_ids = {item.evidence_id for item in lifecycle}
    if lifecycle_ids != set(freshness_by_id):
        raise ValueError("lifecycle/freshness evidence set mismatch")
    records = tuple(sorted(
        (
            EvidenceRecord(
                item.identity,
                item.stage,
                item.evidence_id,
                freshness_by_id[item.evidence_id],
                item.reason,
            )
            for item in lifecycle
        ),
        key=lambda record: record.evidence_id,
    ))
    report = EvidenceReport(records)
    report.validate()
    return report
