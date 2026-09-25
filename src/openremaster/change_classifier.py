from __future__ import annotations
from pathlib import PurePosixPath
from .domains import Domain

_RULES: tuple[tuple[tuple[str, ...], Domain], ...] = (
    (("texture", "textures", "sprite", "sprites", "asset", "assets"), Domain.ASSETS),
    (("room", "rooms", "geometry", "mesh", "collision"), Domain.GEOMETRY),
    (("movement", "player", "controller", "stairs"), Domain.MOVEMENT),
    (("portal", "portals", "transition", "transitions"), Domain.TRANSITIONS),
    (("puzzle", "puzzles", "interaction", "trigger"), Domain.PUZZLES),
    (("audio", "sound", "sounds", "music", "wav"), Domain.AUDIO),
    (("locale", "localization", "i18n", "strings", "dialog"), Domain.LOCALIZATION),
    (("save", "load", "persistence"), Domain.SAVE_LOAD),
)

def classify_path(path: str) -> frozenset[Domain]:
    normalized = str(PurePosixPath(path)).lower()
    tokens = set(normalized.replace(".", "/").replace("-", "/").replace("_", "/").split("/"))
    domains = {domain for needles, domain in _RULES if any(n in tokens for n in needles)}
    return frozenset(domains)

def classify_paths(paths: list[str]) -> frozenset[Domain]:
    result: set[Domain] = set()
    for path in paths:
        result.update(classify_path(path))
    return frozenset(result)
