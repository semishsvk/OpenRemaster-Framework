import json
import pytest
from openremaster.evidence import EvidenceKey, EvidenceNode
from openremaster.store import JsonEvidenceStore

def test_store_round_trip_and_digest(tmp_path):
    node = EvidenceNode(EvidenceKey("p", "sha", "inputs", "tool", "1", "check"), "pass")
    store = JsonEvidenceStore(tmp_path)
    stored = store.put(node)
    assert store.get(stored.evidence_id).node == node
    assert len(store.artifact_digest(stored.evidence_id)) == 64

def test_store_detects_tampered_identity(tmp_path):
    node = EvidenceNode(EvidenceKey("p", "sha", "inputs", "tool", "1", "check"), "pass")
    store = JsonEvidenceStore(tmp_path)
    stored = store.put(node)
    path = store._path(stored.evidence_id)
    payload = json.loads(path.read_text())
    payload["id"] = "0" * 64
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="identity mismatch"):
        store.get(stored.evidence_id)
