"""Isolated OpenRemaster cross-cutting evidence and behavior contracts.

No live orchestrator, OS, signer, service or game access. This is a
negative-first, non-dispatching reference adapter for existing gates.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict, deque
import hashlib
import json
import re

SHA = re.compile(r"^[a-fA-F0-9]{64}$")
REQUIRED_BEHAVIOR = frozenset({
    "INPUT", "HANDLER", "STATE", "ANIMATION", "INVENTORY",
    "AUDIO", "TRANSITION", "SAVE_LOAD"
})

def good_sha(value: str) -> bool:
    return isinstance(value, str) and bool(SHA.fullmatch(value))

def canonical_digest(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class EvidenceNode:
    key: str
    project: str
    digest: str
    kind: str
    parents: tuple[str, ...] = ()
    independent_validation: str = ""

class EvidenceGraph:
    """Strict per-game DAG, optional framework-tool dependency with proof digest."""
    def __init__(self, nodes: list[EvidenceNode], external_validation=None):
        self.nodes: dict[str, EvidenceNode] = {}
        self.children: dict[str, set[str]] = defaultdict(set)
        for node in nodes:
            if not node.key or not node.project or not node.kind or not good_sha(node.digest):
                raise ValueError("INVALID_EVIDENCE_NODE")
            if node.key in self.nodes:
                raise ValueError("DUPLICATE_EVIDENCE_KEY")
            if len(set(node.parents)) != len(node.parents):
                raise ValueError("DUPLICATE_PARENT")
            self.nodes[node.key] = node
        for node in nodes:
            for parent_key in node.parents:
                parent = self.nodes.get(parent_key)
                if parent is None:
                    raise ValueError("MISSING_DEPENDENCY")
                if parent.project != node.project:
                    if not (parent.project == "OpenRemaster"
                            and parent.kind == "validated_shared_tool"
                            and good_sha(parent.independent_validation)
                            and callable(external_validation)
                            and external_validation(parent) is True):
                        raise ValueError("CROSS_GAME_DEPENDENCY_NOT_VALIDATED")
                self.children[parent_key].add(node.key)
        visited: dict[str, int] = {}
        def walk(key: str) -> None:
            if visited.get(key) == 1:
                raise ValueError("EVIDENCE_CYCLE")
            if visited.get(key) == 2:
                return
            visited[key] = 1
            for parent_key in self.nodes[key].parents:
                walk(parent_key)
            visited[key] = 2
        for key in self.nodes:
            walk(key)

    def downstream(self, changed_keys: set[str]) -> list[str]:
        """Return only transitive dependents in deterministic parent-before-child order."""
        if not changed_keys.issubset(self.nodes):
            raise ValueError("UNKNOWN_CHANGED_EVIDENCE")
        seen = set(changed_keys)
        queue = deque(sorted(changed_keys))
        while queue:
            key = queue.popleft()
            for child in sorted(self.children[key]):
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        affected = seen - changed_keys
        indegrees = {k: sum(p in affected for p in self.nodes[k].parents) for k in affected}
        ready = sorted(k for k in affected if indegrees[k] == 0)
        ordered = []
        while ready:
            key = ready.pop(0)
            ordered.append(key)
            for child in self.children[key]:
                if child in indegrees:
                    indegrees[child] -= 1
                    if indegrees[child] == 0:
                        ready.append(child)
                        ready.sort()
        if len(ordered) != len(affected):
            raise ValueError("EVIDENCE_CYCLE")
        return ordered

    def invalidation(self, previous_digests: dict[str, str]) -> dict:
        """Missing/changed leaf or parent invalidates dependent claims, not every game."""
        changed = {key for key, node in self.nodes.items()
                   if previous_digests.get(key) != node.digest}
        return {
            "changed": sorted(changed),
            "invalidate": self.downstream(changed),
            "status": "REVERIFY_REQUIRED" if changed else "NO_CHANGE",
            "may_promote_fidelity": False,
        }

@dataclass(frozen=True)
class BehaviorEvent:
    tick: int
    kind: str
    effect: str

@dataclass(frozen=True)
class BehaviorReplay:
    project: str
    corpus_sha256: str
    original_capture_sha256: str
    candidate_capture_sha256: str
    original_witness_sha256: str
    candidate_witness_sha256: str
    capture_point: str
    original_point: str
    candidate_point: str
    original: tuple[BehaviorEvent, ...]
    candidate: tuple[BehaviorEvent, ...]

def evaluate_behavior(replay: BehaviorReplay,
                      required_kinds: frozenset[str] = REQUIRED_BEHAVIOR,
                      tick_tolerance: int = 0) -> dict:
    """Independent-acceptance CANDIDATE only; not actual original fidelity certification.

    A witness hash is a reference, not verification of signature or provenance.
    Production ORCH-K003 must independently open, hash and authenticate evidence.
    """
    if tick_tolerance < 0:
        raise ValueError("INVALID_TIMING_TOLERANCE")
    base = {"status": "HOLD", "can_claim_playable": False,
            "can_claim_fidelity_verified": False}
    if not replay.project or not replay.capture_point:
        return {**base, "reason": "MISSING_IDENTITY_OR_CAPTURE"}
    hashes = (replay.corpus_sha256, replay.original_capture_sha256,
              replay.candidate_capture_sha256, replay.original_witness_sha256,
              replay.candidate_witness_sha256)
    if not all(good_sha(x) for x in hashes):
        return {**base, "reason": "MISSING_OR_UNVERIFIED_PROVENANCE"}
    if replay.original_point != replay.capture_point or replay.candidate_point != replay.capture_point:
        return {**base, "reason": "ORACLE_ALIGNMENT_BLOCKED"}
    for sequence in (replay.original, replay.candidate):
        if not sequence or any(evt.tick < 0 or not evt.kind or not evt.effect for evt in sequence):
            return {**base, "reason": "TRACE_INCOMPLETE"}
        if any(a.tick > b.tick for a, b in zip(sequence, sequence[1:])):
            return {**base, "reason": "NONMONOTONIC_TICKS"}
    original_types = {e.kind for e in replay.original}
    if required_kinds - original_types:
        return {**base, "reason": "ORIGINAL_BEHAVIOR_COVERAGE_INSUFFICIENT",
                "missing": sorted(required_kinds - original_types)}
    if len(replay.original) != len(replay.candidate):
        return {**base, "reason": "BEHAVIOR_MISMATCH", "first_difference": "length"}
    for index, (a, b) in enumerate(zip(replay.original, replay.candidate)):
        if a.kind != b.kind or a.effect != b.effect or abs(a.tick - b.tick) > tick_tolerance:
            return {**base, "reason": "BEHAVIOR_MISMATCH", "first_difference": index}
    return {
        "status": "SHADOW_REPLAY_COMPARISON_MATCH",
        "reason": "REQUIRES_INDEPENDENT_ORIGINAL_AND_NATIVE_ATTESTATION",
        "compared_events": len(replay.original),
        "can_claim_playable": False,
        "can_claim_fidelity_verified": False,
    }
