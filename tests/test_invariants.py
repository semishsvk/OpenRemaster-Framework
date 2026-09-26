from openremaster.bundle import ReplayEvidenceBundle
from openremaster.golden import GoldenInventory, GoldenRoom, GoldenState
from openremaster.golden_links import GoldenEvidenceLink
from openremaster.invariants import validate_cross_component
from openremaster.replay import InputFrame, ReplayContract
from openremaster.trace import RuntimeTrace, StateCheckpoint
from openremaster.visual import CameraPose, RenderConfig, VisualCaptureContract

def inventory():
    return GoldenInventory("1","p","sha",(GoldenRoom("room",(GoldenState("default","Default"),),()),))

def test_matching_components_are_valid():
    r = ReplayContract("1","p","sha","runtime","1",60,0,(InputFrame(0),),"room","default")
    bundle = ReplayEvidenceBundle("1",r,RuntimeTrace(r.digest(), checkpoints=(StateCheckpoint(0,"state"),)))
    visual = VisualCaptureContract("1","p","sha","room","cam",CameraPose((0,0,0),(0,0,0),70),RenderConfig(1,1,"neutral","r","1"),"state","default")
    link = GoldenEvidenceLink("room","default",bundle.digest(),visual.digest(),"")
    assert validate_cross_component(inventory(),link,bundle,visual).valid

def test_revision_drift_is_rejected():
    r = ReplayContract("1","p","old","runtime","1",60,0,(InputFrame(0),))
    bundle = ReplayEvidenceBundle("1",r,RuntimeTrace(r.digest()))
    link = GoldenEvidenceLink("room","default",bundle.digest(),"","")
    result = validate_cross_component(inventory(),link,bundle)
    assert not result.valid
    assert "replay source revision mismatch" in result.errors

def test_unknown_room_state_is_rejected():
    result = validate_cross_component(inventory(),GoldenEvidenceLink("missing","default"))
    assert not result.valid
