from __future__ import annotations
from dataclasses import asdict
import json
from .impact_rules import DomainImpactPlan
from .policy import ValidationPolicy
from .provenance import ProvenanceRecord

def invalidation_report(
    impact: DomainImpactPlan,
    policy: ValidationPolicy,
    provenance: tuple[ProvenanceRecord, ...],
) -> str:
    payload = {
        "schema_version": "1",
        "changed_domains": sorted(d.value for d in impact.changed),
        "invalidated_domains": sorted(d.value for d in impact.invalidated),
        "validation_policy": asdict(policy),
        "checks": [asdict(record) for record in provenance],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
