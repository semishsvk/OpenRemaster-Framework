"""Pure bounded analysis. Source alternatives never constitute runtime proof."""
from collections import deque
import hashlib
import json
import re

CLASSES = dict(zip((f"SL-{i:02}" for i in range(1, 13)), (
    "Lost Critical Item", "Unrecoverable Item Ownership", "Irreversible Puzzle State",
    "Stranded Character", "Broken Door State", "Unreachable Interaction",
    "Script Dependency Deadlock", "Inventory Capacity Trap", "Missed Timed Opportunity",
    "Broken Actor Handoff", "Save-State Corruption", "False Victory / Unreachable Ending")))
STATUSES = {"STATIC_CANDIDATE", "SOURCE_VERIFIED", "RUNTIME_REFERENCE_VERIFIED",
            "REMASTER_REPLAY_VERIFIED", "CONFIRMED_REGRESSION",
            "INTENDED_ORIGINAL_DEAD_END", "UNRESOLVED", "HOLD"}


class Hold(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Hold(reason)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def read_pinned(path, expected, max_bytes=32 * 1024 * 1024):
    require(path.stat().st_size <= max_bytes, "INPUT_BYTES_LIMIT")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, "EVIDENCE_HASH_DRIFT")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(Hold("NONFINITE_JSON")))


def reachability(states, transitions, start, endings, *, complete=False, limit=4096):
    """Explicit adapter-supplied states only; unknown guards remain possible edges.

    Returns graph properties, never authentic-game reachability or hard-softlock proof.
    No unbounded state generation; false guards excluded, unknown guards cannot prove paths.
    """
    require(type(limit) is int and 0 < limit <= 100000, "INVALID_BOUND")
    require(len(states) <= limit and len(transitions) <= limit * 16, "GRAPH_BOUND")
    require(len(set(states)) == len(states) and start in states, "STATE_IDENTITY")
    require(set(endings) <= set(states), "ENDING_UNKNOWN_STATE")
    forward = {s: [] for s in states}
    backward = {s: [] for s in states}
    uncertain = False
    for edge in transitions:
        require(edge["from"] in forward and edge["to"] in forward, "DANGLING_STATE")
        guard = edge.get("guard")
        require(guard is None or type(guard) is bool, "GUARD_MUST_BE_EXPLICIT")
        uncertain |= guard is None
        if guard is not False:
            forward[edge["from"]].append((edge["to"], guard))
            backward[edge["to"]].append((edge["from"], guard))

    def walk(seeds, graph, certain):
        seen = set(seeds)
        queue = deque(seeds)
        while queue:
            for dest, guard in graph[queue.popleft()]:
                if dest not in seen and (not certain or guard is True):
                    seen.add(dest)
                    queue.append(dest)
        return seen
    reachable = walk([start], forward, True)
    possible = walk([start], forward, False)
    recoverable = walk(endings, backward, True)
    possibly_recoverable = walk(endings, backward, False)
    scope_closed = complete is True and bool(endings) and not uncertain
    return {"status": "PASS" if scope_closed else "HOLD", "scope": "SUPPLIED_MODEL_ONLY",
            "reachable": sorted(reachable), "possibly_reachable": sorted(possible),
            "recoverable": sorted(recoverable),
            "unreachable_in_model": sorted(set(states) - possible),
            "dead_end_candidates": sorted(reachable - possibly_recoverable) if endings else [],
            "unproven": sorted(possible - reachable), "model_closed": scope_closed,
            "confirmed_softlocks": 0, "original_game_validated": False}


def validate_finding(finding):
    require(finding.get("class") in CLASSES, "UNKNOWN_SOFTLOCK_CLASS")
    require(finding.get("status") in STATUSES, "UNKNOWN_EVIDENCE_STATUS")
    for key in ("project", "game_version", "source_sha256", "location", "unknowns"):
        require(key in finding, "MISSING_" + key.upper())
    require(isinstance(finding["unknowns"], list), "UNKNOWNS_TYPE")
    require(type(finding["source_sha256"]) is str and
            re.fullmatch(r"[a-f0-9]{64}", finding["source_sha256"]), "INVALID_SOURCE_HASH")
    status = finding["status"]
    # This local tool has no trusted reviewer/oracle verifier. Reject promotion
    # rather than trusting self-asserted booleans, paths, signatures, or screenshots.
    require(status in {"STATIC_CANDIDATE", "UNRESOLVED", "HOLD"},
            "INDEPENDENT_EVIDENCE_VERIFIER_REQUIRED")
    require(not finding.get("unwinnable_proven") and not finding.get("runtime_verified"),
            "STATIC_CLAIM_PROMOTION_FORBIDDEN")
    return {"status": status, "classification": CLASSES[finding["class"]],
            "finding_digest": digest(finding), "hard_softlock_proven": False}


def state_roundtrip(before, after):
    required = {"actors", "inventory", "timers", "scripts", "rooms", "globals", "camera"}
    require(type(before) is dict and type(after) is dict and
            required <= before.keys() and required <= after.keys(), "INCOMPLETE_SAVE_STATE")
    require(all(value is not None for doc in (before, after) for value in doc.values()),
            "UNKNOWN_SAVE_STATE")
    changes = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    return {"status": "FAIL" if changes else "PASS", "scope": "SUPPLIED_STATE_ONLY",
            "differences": changes, "native_roundtrip_verified": False}


def shadow_proposal(project, checkpoint, dependencies, completed, mode="UNKNOWN"):
    """Dependency-aware proposal, not a scheduler or admission verifier."""
    require(mode in {"NORMAL", "LIGHT", "GAMING", "UNKNOWN"}, "UNKNOWN_GOVERNOR_MODE")
    missing = sorted(set(dependencies) - set(completed))
    return {"project": project, "checkpoint": checkpoint, "status": "HOLD",
            "missing_dependencies": missing, "mode": mode, "max_heavy_slots": 3,
            "budget": {"seconds": 30, "max_states": 4096, "heavy_slots_requested": 0},
            "suggestion": "LIGHT_HEADLESS_ANALYSIS" if not missing else "RESOLVE_DEPENDENCIES",
            "required_admission": ["FRESH_PROJECT_OWNER", "SINGLE_WRITER", "GOVERNOR", "K003"],
            "may_dispatch": False, "may_acquire_lease": False, "may_sign": False,
            "production_admitted": False, "auto_retry": False, "trust": "UNTRUSTED_DEV"}


def production_gate(_evidence):
    # Structural evidence does not establish trust. Existing independently commissioned
    # production policy must verify identities, signatures and release authority.
    return {"status": "HOLD", "reason": "INDEPENDENT_PRODUCTION_VERIFIER_NOT_BOUND",
            "may_release": False, "may_sign": False}
