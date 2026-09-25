from openremaster.change_classifier import classify_path, classify_paths
from openremaster.domains import Domain

def test_classifies_known_project_paths():
    assert Domain.GEOMETRY in classify_path("game/rooms/well/collision.tres")
    assert Domain.AUDIO in classify_path("assets/audio/ambient/well.wav")
    assert Domain.SAVE_LOAD in classify_path("runtime/save/load_manager.gd")

def test_combines_multiple_changed_paths():
    domains = classify_paths(["assets/textures/keyhole.png", "game/portals/well.gd"])
    assert domains == frozenset({Domain.ASSETS, Domain.TRANSITIONS})
