"""Regressions for the frozen Phase 1 acceptance boundary."""
from dataclasses import replace
from hashlib import sha256
import json
import pytest

from openremaster.archaeology import BinarySource, ByteRange, DecoderContract, DecodedRecord
from openremaster.bundle import ReplayEvidenceBundle
from openremaster.cache import CacheDecision, CacheRequest, EvidenceCache
from openremaster.coverage import CoverageEvidence, analyze_coverage
from openremaster.evidence import EvidenceDependency, EvidenceGraph, EvidenceKey, EvidenceNode
from openremaster.failure_reproducer import build_failure_window
from openremaster.golden import GoldenInventory, GoldenRoom, GoldenState
from openremaster.golden_links import GoldenEvidenceLink
from openremaster.invariants import validate_cross_component
from openremaster.manifest import ProjectManifest
from openremaster.replay import InputFrame, ReplayContract
from openremaster.replay_slice import slice_replay
from openremaster.snapshot import SourceSnapshot
from openremaster.trace import RuntimeTrace, StateCheckpoint
from openremaster.visual import CameraPose, RenderConfig, VisualCaptureContract


def digest(value):
    return sha256(value.encode()).hexdigest()


@pytest.mark.parametrize("field", (
    "project_id", "source_revision", "input_digest", "tool_id", "tool_version", "check_id",
))
def test_cache_requires_every_identity_field(field):
    key = EvidenceKey("p", "sha", "inputs", "tool", "1", "check")
    changed = replace(key, **{field: "different"})
    assert changed.stable_id() != key.stable_id()
    cache = EvidenceCache((EvidenceNode(key, "pass"),))
    assert cache.decide(CacheRequest(changed)).decision is CacheDecision.RERUN


@pytest.mark.parametrize("status", ("fail", "unknown"))
def test_nonpass_cache_never_satisfies_pass_request(status):
    key = EvidenceKey("p", "sha", "inputs", "tool", "1", "check")
    assert EvidenceCache((EvidenceNode(key, status),)).decide(CacheRequest(key)).decision is CacheDecision.RERUN


def test_evidence_serialization_rejects_dangling_dependency_and_schema_drift():
    node = EvidenceNode(EvidenceKey("p", "sha", "inputs", "tool", "1", "check"), "pass")
    payload = json.loads(EvidenceGraph((node,)).to_json())
    payload["nodes"][0]["dependencies"] = [{"evidence_id": "missing", "kind": "input"}]
    with pytest.raises(ValueError, match="missing evidence dependency"):
        EvidenceGraph.from_json(json.dumps(payload))
    with pytest.raises(ValueError, match="missing evidence dependency"):
        EvidenceGraph((replace(node, dependencies=(EvidenceDependency("missing"),)),)).to_json()
    payload["schema_version"] = "2"
    with pytest.raises(ValueError, match="schema"):
        EvidenceGraph.from_json(json.dumps(payload))


@pytest.mark.parametrize("field", ("project_id", "repository", "revision", "manifest_digest"))
def test_source_snapshot_binds_each_identity_field(field):
    snapshot = SourceSnapshot("p", "owner/p", "sha", "manifest")
    assert snapshot.digest() == replace(snapshot).digest()
    assert snapshot.digest() != replace(snapshot, **{field: "other"}).digest()


def test_manifest_rejects_missing_project_identity():
    with pytest.raises(ValueError, match="project_id"):
        ProjectManifest("1", " ", "Project", "adapter").validate()


def components():
    inventory = GoldenInventory("1", "p", "sha", (
        GoldenRoom("ziggurat", (GoldenState("a", "A"), GoldenState("b", "B"))),
    ))
    replay = ReplayContract("1", "p", "sha", "runtime", "1", 60, 7,
                            tuple(InputFrame(i) for i in range(4)), "ziggurat", "a")
    bundle = ReplayEvidenceBundle("1", replay, RuntimeTrace(replay.digest(), (), (StateCheckpoint(0, "world"),)))
    visual = VisualCaptureContract("1", "p", "sha", "ziggurat", "overview",
                                   CameraPose((0, 0, 0), (0, 0, 0), 70),
                                   RenderConfig(640, 480, "original-1996", "renderer", "1"), "world", "a")
    link = GoldenEvidenceLink("ziggurat", "a", bundle.digest(), visual.digest())
    return inventory, link, bundle, visual


@pytest.mark.parametrize("field,value", (
    ("runtime_id", "other"), ("runtime_version", "2"), ("seed", 8),
    ("fixed_tick_hz", 30), ("room_id", "room"), ("state_id", "b"),
))
def test_replay_identity_context(field, value):
    replay = components()[2].replay
    assert replace(replay, **{field: value}).digest() != replay.digest()


@pytest.mark.parametrize("field,value", (
    ("camera_id", "detail"), ("source_revision", "old"), ("state_digest", "other-world"),
    ("state_id", "b"), ("camera", CameraPose((1, 0, 0), (0, 0, 0), 70)),
    ("render", RenderConfig(800, 600, "original-1996", "renderer", "1")),
))
def test_visual_identity_context(field, value):
    visual = components()[3]
    assert replace(visual, **{field: value}).digest() != visual.digest()


def test_cross_component_consistent_fixture():
    assert validate_cross_component(*components()).valid


@pytest.mark.parametrize("field,value", (
    ("project_id", "other"), ("source_revision", "old"),
    ("room_id", "other"), ("state_id", "b"), ("room_id", ""), ("state_id", ""),
))
def test_cross_component_replay_drift_fails_even_with_updated_digest(field, value):
    inventory, link, bundle, visual = components()
    replay = replace(bundle.replay, **{field: value})
    bundle = replace(bundle, replay=replay, trace=replace(bundle.trace, replay_digest=replay.digest()))
    link = replace(link, replay_bundle_digest=bundle.digest())
    assert not validate_cross_component(inventory, link, bundle, visual).valid


@pytest.mark.parametrize("field,value", (
    ("project_id", "other"), ("source_revision", "old"),
    ("scene_id", "other"), ("state_id", "b"), ("state_id", ""),
))
def test_cross_component_visual_drift_fails_even_with_updated_digest(field, value):
    inventory, link, bundle, visual = components()
    visual = replace(visual, **{field: value})
    link = replace(link, visual_baseline_digest=visual.digest())
    assert not validate_cross_component(inventory, link, bundle, visual).valid


@pytest.mark.parametrize("field", ("replay_bundle_digest", "visual_baseline_digest"))
@pytest.mark.parametrize("value", ("", digest("wrong")))
def test_cross_component_requires_exact_link_digest(field, value):
    inventory, link, bundle, visual = components()
    assert not validate_cross_component(inventory, replace(link, **{field: value}), bundle, visual).valid


def test_cross_component_missing_referenced_objects_is_not_verified():
    inventory, link, bundle, visual = components()
    assert not validate_cross_component(inventory, link, None, visual).valid
    assert not validate_cross_component(inventory, link, bundle, None).valid


def test_cross_component_world_state_digest_must_match_replay_checkpoint():
    inventory, link, bundle, visual = components()
    visual = replace(visual, state_digest="different-world")
    link = replace(link, visual_baseline_digest=visual.digest())
    assert not validate_cross_component(inventory, link, bundle, visual).valid
    inventory, link, bundle, visual = components()
    bundle = replace(bundle, trace=replace(bundle.trace, checkpoints=()))
    link = replace(link, replay_bundle_digest=bundle.digest())
    assert not validate_cross_component(inventory, link, bundle, visual).valid


def test_slice_requires_explicit_world_checkpoint_and_preserves_context():
    replay = components()[2].replay
    with pytest.raises(ValueError, match="initial state digest"):
        slice_replay(replay, 1, 3, "")
    sliced = slice_replay(replay, 1, 3, "world")
    assert (sliced.replay.room_id, sliced.replay.state_id) == (replay.room_id, replay.state_id)
    assert sliced.replay.seed == replay.seed
    assert [f.tick for f in sliced.replay.frames] == [0, 1, 2]
    trace = RuntimeTrace(replay.digest(), (), (StateCheckpoint(0, ""),))
    with pytest.raises(ValueError, match="initial state digest"):
        build_failure_window(replay, trace, 3)


def test_coverage_requires_each_room_state_and_evidence_kind():
    inventory = components()[0]
    evidence = (CoverageEvidence("ziggurat", "a", "visual", digest("image")),
                CoverageEvidence("ziggurat", "b", "replay", digest("replay")))
    visual = analyze_coverage(inventory, evidence, "visual")
    replay = analyze_coverage(inventory, evidence, "replay")
    assert visual.required == replay.required == 2
    assert visual.missing == (("ziggurat", "b"),)
    assert replay.missing == (("ziggurat", "a"),)


def test_archaeology_preserves_exact_range_and_decoder_provenance():
    source = BinarySource("binary", digest("source"), 32)
    byte_range = ByteRange("binary", 7, 11, digest("bytes"))
    byte_range.validate(source)
    with pytest.raises(ValueError, match="source mismatch"):
        byte_range.validate(replace(source, source_id="other"))
    decoder = DecoderContract("generic", "1", "format", digest("params"))
    record = DecodedRecord("record", byte_range, decoder.digest(), digest("output"), "entry")
    record.validate()
    assert (record.source_range.offset, record.source_range.length) == (7, 11)
    assert record.source_range.digest == digest("bytes")
    assert decoder.digest() != replace(decoder, decoder_version="2").digest()
    assert decoder.digest() != replace(decoder, parameters_digest=digest("changed")).digest()


@pytest.mark.parametrize("offset,length", ((-1, 1), (0, -1), (31, 2)))
def test_archaeology_rejects_out_of_bounds_ranges(offset, length):
    with pytest.raises(ValueError, match="outside"):
        ByteRange("binary", offset, length, digest("bytes")).validate(BinarySource("binary", digest("source"), 32))
