from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256

from .evidence import EvidenceDependency, EvidenceGraph, EvidenceKey, EvidenceNode
from .freshness import ProvenanceFreshness
from .identity import EvidenceIdentity
from .lifecycle import EvidenceStage, LifecycleEvidence


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OpenCadaverPhase2Fixture:
    graph: EvidenceGraph
    lifecycle: tuple[LifecycleEvidence, ...]
    source_id: str
    framing_id: str
    support_id: str

    def freshness_after_source_change(self):
        return ProvenanceFreshness(self.graph).evaluate({self.source_id})


def build_opencadaver_verified_fixture() -> OpenCadaverPhase2Fixture:
    """Minimal real-consumer fixture based on the VERIFIED K133/K134/K137 chain.

    It intentionally models only framework-relevant claims:
    K133 observes embedded 288-byte MP3 payloads in decoded LEV4.MP1;
    K134 derives 16-byte row stride and descriptor row-count semantics;
    K137 derives encoded support of 16 * word17 rows.
    """
    project = "opencadaver"
    revision = "49f6b7c517f11cadbe464495a343a5399c079067"
    corpus = "cadaver-retail"
    room = "global"
    state = "decoded-corpus"
    run = "verified-k133-k137"

    graph = EvidenceGraph()
    source_key = EvidenceKey(project, revision, _digest("LEV4.MP1 decoded corpus"), "re-corpus", "K133", "embedded-mp3-payload")
    source_id = graph.add(EvidenceNode(source_key, "pass"))

    framing_key = EvidenceKey(project, revision, _digest(source_id), "re-analysis", "K134", "mp3-row-framing")
    framing_id = graph.add(EvidenceNode(framing_key, "pass", (EvidenceDependency(source_id, "input"),)))

    support_key = EvidenceKey(project, revision, _digest(framing_id), "re-analysis", "K137", "encoded-support")
    support_id = graph.add(EvidenceNode(support_key, "pass", (EvidenceDependency(framing_id, "derived"),)))
    graph.validate_references()

    identities = (
        EvidenceIdentity("2", project, corpus, "K133-embedded-mp3", room, state, run, revision, _digest("root")),
        EvidenceIdentity("2", project, corpus, "K134-row-framing", room, state, run, revision, _digest(source_id)),
        EvidenceIdentity("2", project, corpus, "K137-encoded-support", room, state, run, revision, _digest(framing_id)),
    )
    lifecycle = tuple(
        LifecycleEvidence(identity, EvidenceStage.VALIDATED, evidence_id)
        for identity, evidence_id in zip(identities, (source_id, framing_id, support_id))
    )
    for item in lifecycle:
        item.validate()

    return OpenCadaverPhase2Fixture(graph, lifecycle, source_id, framing_id, support_id)
