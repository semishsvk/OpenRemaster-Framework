from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Reference:
    source_record: str
    target_record: str
    relation: str
    source_field: str = ""

class ReferenceGraph:
    def __init__(self) -> None:
        self.records: set[str] = set()
        self.references: list[Reference] = []

    def add_record(self, record_id: str) -> None:
        self.records.add(record_id)

    def add_reference(self, reference: Reference) -> None:
        if reference.source_record not in self.records or reference.target_record not in self.records:
            raise ValueError("reference endpoint missing")
        self.references.append(reference)

    def outgoing(self, record_id: str) -> tuple[Reference, ...]:
        return tuple(sorted(
            (r for r in self.references if r.source_record == record_id),
            key=lambda r: (r.target_record, r.relation, r.source_field),
        ))

    def incoming(self, record_id: str) -> tuple[Reference, ...]:
        return tuple(sorted(
            (r for r in self.references if r.target_record == record_id),
            key=lambda r: (r.source_record, r.relation, r.source_field),
        ))

    def dangling_targets(self) -> tuple[str, ...]:
        # Endpoints are validated on insertion; retained as an explicit audit primitive.
        return ()
