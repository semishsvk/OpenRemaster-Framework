import pytest
from openremaster.coverage import CoverageEvidence, analyze_coverage
from openremaster.golden import GoldenInventory, GoldenRoom, GoldenState

def inventory():
    return GoldenInventory(
        "1", "openazrael", "sha",
        (
            GoldenRoom("room-1", (GoldenState("default","Default"),), ("keyhole",)),
            GoldenRoom("ziggurat", (
                GoldenState("a","State A"),
                GoldenState("b","State B"),
            ), ()),
        ),
    )

def test_inventory_digest_is_deterministic():
    assert inventory().digest() == inventory().digest()

def test_multistate_room_counts_each_state():
    report = analyze_coverage(
        inventory(),
        (
            CoverageEvidence("room-1","default","visual","a"),
            CoverageEvidence("ziggurat","a","visual","b"),
        ),
        "visual",
    )
    assert report.required == 3
    assert report.covered == 2
    assert report.missing == (("ziggurat","b"),)
    assert not report.complete

def test_complete_coverage():
    evidence = tuple(
        CoverageEvidence(room, state, "replay", "digest")
        for room, state in (("room-1","default"),("ziggurat","a"),("ziggurat","b"))
    )
    assert analyze_coverage(inventory(), evidence, "replay").complete

def test_unsorted_rooms_rejected():
    bad = GoldenInventory("1","p","sha",(
        GoldenRoom("z"), GoldenRoom("a")
    ))
    with pytest.raises(ValueError, match="rooms"):
        bad.validate()
