"""ResourceResolutionContract.v1 and SemanticPopulationGuard.v1.
Definitions, references, runtime instances and patch-layer provenance stay distinct.
"""
from collections import Counter
from pathlib import Path
from alignment import is_hash, hash_file


def attest(root, name, expected):
    if root is None or not is_hash(expected) or not isinstance(name, str) or not name:
        return False
    if Path(name).is_absolute() or ':' in name or '\\' in name or '..' in Path(name).parts:
        return False
    try:
        base = Path(root).resolve(strict=True)
        item = (base / name).resolve(strict=True)
        return base in item.parents and item.is_file() and hash_file(item).lower() == expected.lower()
    except (OSError, ValueError, TypeError):
        return False


def normalize_resource_path(value):
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("INVALID_RESOURCE_PATH")
    name = value.replace("\\", "/")
    if name.startswith("/") or ":" in name:
        raise ValueError("INVALID_RESOURCE_PATH")
    bits = [piece for piece in name.split("/") if piece not in ("", ".")]
    if not bits or ".." in bits:
        raise ValueError("INVALID_RESOURCE_PATH")
    return "/".join(piece.casefold() for piece in bits)


def resolve_resources(manifest, requested, evidence_root=None):
    """Explicit order is mandatory; no hardcoded Fallout/Ultima precedence."""
    problems = []
    if not isinstance(manifest, dict) or manifest.get("schema") != "ResourceResolutionContract.v1":
        return {"schema": "ResourceResolutionResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "problems": ["SCHEMA"], "resolved": []}
    order, layers = manifest.get("resolution_order"), manifest.get("layers")
    if not isinstance(order, list) or not isinstance(layers, list):
        return {"schema": "ResourceResolutionResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "problems": ["LAYERS_OR_ORDER"], "resolved": []}
    if (not all(isinstance(x, str) and x for x in order) or
        not all(isinstance(x, dict) and isinstance(x.get("id"), str) and x["id"]
                for x in layers)):
        return {"schema": "ResourceResolutionResult.v1",
                "status": "INSUFFICIENT_EVIDENCE",
                "problems": ["MALFORMED_LAYER_IDS"], "resolved": []}
    if len(order) != len(set(order)) or len(order) != len(layers):
        problems.append("DUPLICATE_OR_MISSING_LAYER_ORDER")
    by_id = {x["id"]: x for x in layers}
    if set(order) != set(by_id) or len(by_id) != len(layers):
        problems.append("LAYER_IDS_NOT_BIJECTIVE")
    for layer in layers:
        if not isinstance(layer, dict) or not is_hash(layer.get("source_sha256")):
            problems.append("LAYER_SOURCE_FINGERPRINT_MISSING")
    if not is_hash(manifest.get("order_evidence_sha256")):
        problems.append("ORDER_PROVENANCE_MISSING")
    if manifest.get("order_evidence_state") not in ("VALIDATED", "HYPOTHESIS"):
        problems.append("ORDER_EVIDENCE_STATE_INVALID")
    if problems:
        return {"schema": "ResourceResolutionResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "problems": sorted(set(problems)), "resolved": []}

    layer_rows = {}
    for ident in order:
        layer_rows[ident] = {}
        entries = by_id[ident].get("entries")
        if not isinstance(entries, list):
            problems.append("ENTRIES_MISSING_" + ident)
            continue
        for row in entries:
            try:
                key = normalize_resource_path(row.get("path"))
                if not is_hash(row.get("sha256")) or not isinstance(row.get("size"), int) or row["size"] < 0:
                    raise ValueError("FILE_PROVENANCE_INVALID")
                layer_rows[ident].setdefault(key, []).append(row)
            except (ValueError, TypeError, AttributeError):
                problems.append("INVALID_ENTRY_" + ident)
    if not isinstance(requested, list):
        problems.append("REQUESTS_INVALID")
    if problems:
        return {"schema": "ResourceResolutionResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "problems": sorted(set(problems)), "resolved": []}

    out = []
    for path in requested:
        try:
            key = normalize_resource_path(path)
        except ValueError:
            problems.append("INVALID_REQUEST_PATH")
            continue
        candidates = []
        ambiguous = False
        for ident in order:
            matches = layer_rows[ident].get(key, [])
            if matches:
                identity_set = {(r["sha256"].lower(), r["size"]) for r in matches}
                if len(identity_set) != 1:
                    ambiguous = True
                candidates.append({"layer": ident, "source_sha256": by_id[ident]["source_sha256"],
                                   "asset_sha256": matches[0]["sha256"], "size": matches[0]["size"],
                                   "duplicate_records": len(matches)})
        if ambiguous:
            result = "AMBIGUOUS"
        elif not candidates:
            result = "MISSING"
        else:
            result = "RESOLVED"
        out.append({"path": key, "status": result,
                    "winner": candidates[0] if result == "RESOLVED" else None,
                    "candidates_in_precedence_order": candidates})
    if problems or any(row["status"] != "RESOLVED" for row in out):
        status = "BLOCKED"
    elif manifest["order_evidence_state"] != "VALIDATED" or not attest(
        evidence_root, manifest.get("order_evidence_path"), manifest.get("order_evidence_sha256")):
        status = "STRUCTURAL_ONLY"
    else:
        status = "RESOLUTION_CONTRACT_PASS"
    return {"schema": "ResourceResolutionResult.v1", "status": status,
            "problems": sorted(set(problems)), "resolved": out,
            "fidelity_verified": False}


def validate_population(manifest, evidence_root=None):
    """Check reachable/materialized instances, never equate physical pages to entities."""
    problems = []
    if not isinstance(manifest, dict) or manifest.get("schema") != "SemanticPopulationGuard.v1":
        return {"schema": "SemanticPopulationResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "problems": ["SCHEMA"], "counts": {}}
    definitions = manifest.get("definitions")
    instances = manifest.get("instances")
    expectations = manifest.get("expectations")
    if not isinstance(definitions, list) or not isinstance(instances, list) or not isinstance(expectations, dict):
        return {"schema": "SemanticPopulationResult.v1", "status": "INSUFFICIENT_EVIDENCE",
                "problems": ["DEFINITIONS_INSTANCES_EXPECTATIONS_REQUIRED"], "counts": {}}
    def_by_id = {}
    for item in definitions:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str) or
            not isinstance(item.get("kind"), str) or not item["kind"]):
            problems.append("INVALID_DEFINITION")
            continue
        if item["id"] in def_by_id:
            problems.append("DUPLICATE_DEFINITION")
        def_by_id[item["id"]] = item
    by_id = {}
    for obj in instances:
        if not isinstance(obj, dict) or not isinstance(obj.get("id"), str) or not obj["id"]:
            problems.append("INVALID_INSTANCE")
            continue
        if obj["id"] in by_id:
            problems.append("DUPLICATE_INSTANCE")
        by_id[obj["id"]] = obj
        if obj.get("definition_id") not in def_by_id:
            problems.append("UNRESOLVED_DEFINITION")
        if not isinstance(obj.get("active"), bool):
            problems.append("ACTIVE_STATE_UNKNOWN")
    for obj in instances:
        if not isinstance(obj, dict):
            continue
        parent = obj.get("parent_instance_id")
        if parent is not None and parent not in by_id:
            problems.append("UNRESOLVED_PARENT")
    # A source definition may materialize into many runtime instances.
    for ident in by_id:
        seen = set()
        current = ident
        while current is not None and current in by_id:
            if current in seen:
                problems.append("PARENT_CYCLE")
                break
            seen.add(current)
            current = by_id[current].get("parent_instance_id")
    counts = Counter()
    active_total = 0
    for obj in instances:
        if not isinstance(obj, dict) or obj.get("active") is not True:
            continue
        definition = def_by_id.get(obj.get("definition_id"))
        if definition is None:
            continue
        counts[definition["kind"]] += 1
        active_total += 1
    ranges = expectations.get("active_by_kind")
    if not isinstance(ranges, dict) or not ranges:
        problems.append("EXPECTED_POPULATION_MISSING")
    else:
        for kind in set(counts) | set(ranges):
            if not isinstance(kind, str):
                problems.append("INVALID_EXPECTATION_KIND")
                continue
            if kind not in ranges:
                problems.append("UNBOUNDED_ACTIVE_KIND_" + kind)
                continue
            bound = ranges[kind]
            if not (isinstance(bound, dict) and
                    isinstance(bound.get("min"), int) and isinstance(bound.get("max"), int) and
                    0 <= bound["min"] <= bound["max"]):
                problems.append("INVALID_POPULATION_BOUND_" + kind)
            elif not bound["min"] <= counts[kind] <= bound["max"]:
                problems.append("POPULATION_MISMATCH_" + kind)
    # An explicit oracle constraint is needed for semantic promotion.
    oracle_ready = (expectations.get("status") == "CORPUS_AND_RUNTIME_VERIFIED" and
                    attest(evidence_root, expectations.get("evidence_path"),
                           expectations.get("evidence_sha256")))
    if not is_hash(expectations.get("evidence_sha256")):
        problems.append("POPULATION_PROVENANCE_MISSING")
    status = ("FAIL" if any(x.startswith(("POPULATION_MISMATCH", "UNRESOLVED", "DUPLICATE", "PARENT_CYCLE")) for x in problems)
              else "BLOCKED" if problems
              else "POPULATION_CONTRACT_PASS" if oracle_ready else "STRUCTURAL_PASS_SEMANTIC_HOLD")
    return {"schema": "SemanticPopulationResult.v1", "status": status,
            "problems": sorted(set(problems)),
            "counts": {"definitions": len(def_by_id), "instances": len(instances),
                       "active_instances": active_total, "active_by_kind": dict(sorted(counts.items()))},
            "fidelity_verified": False}
