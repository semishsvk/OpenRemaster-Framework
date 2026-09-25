from __future__ import annotations
from enum import Enum

class Domain(str, Enum):
    ASSETS = "assets"
    GEOMETRY = "geometry"
    MOVEMENT = "movement"
    TRANSITIONS = "transitions"
    PUZZLES = "puzzles"
    AUDIO = "audio"
    LOCALIZATION = "localization"
    SAVE_LOAD = "save-load"
    E2E = "e2e"

DEFAULT_DEPENDENCIES: dict[Domain, frozenset[Domain]] = {
    Domain.ASSETS: frozenset(),
    Domain.GEOMETRY: frozenset({Domain.ASSETS}),
    Domain.MOVEMENT: frozenset({Domain.GEOMETRY}),
    Domain.TRANSITIONS: frozenset({Domain.GEOMETRY, Domain.MOVEMENT}),
    Domain.PUZZLES: frozenset({Domain.ASSETS, Domain.TRANSITIONS}),
    Domain.AUDIO: frozenset({Domain.ASSETS}),
    Domain.LOCALIZATION: frozenset(),
    Domain.SAVE_LOAD: frozenset({Domain.PUZZLES, Domain.TRANSITIONS}),
    Domain.E2E: frozenset({
        Domain.MOVEMENT, Domain.TRANSITIONS, Domain.PUZZLES,
        Domain.AUDIO, Domain.LOCALIZATION, Domain.SAVE_LOAD,
    }),
}
