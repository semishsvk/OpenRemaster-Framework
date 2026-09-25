from hashlib import sha256
import pytest
from openremaster.golden_links import GoldenEvidenceLink

def d(v):
    return sha256(v.encode()).hexdigest()

def test_room_state_can_link_all_evidence_classes():
    link = GoldenEvidenceLink("ziggurat","state-a",d("replay"),d("visual"),d("assets"))
    link.validate()

def test_bad_digest_is_rejected():
    with pytest.raises(ValueError, match="sha256"):
        GoldenEvidenceLink("room","state",replay_bundle_digest="bad").validate()
