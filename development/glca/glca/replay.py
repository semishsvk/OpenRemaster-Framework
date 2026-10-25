"""Reuse the byte-pinned Framework First Divergence r2 implementation."""
from pathlib import Path
import hashlib
import importlib
import json
import sys
from .core import require


def diagnose(*args, **kwargs):
    root = Path(__file__).resolve().parent.parent
    pins = json.loads((root / 'INPUT_PINS.json').read_text())
    for name in ('first_divergence_v1.py', 'evidence_cache_v1.py', 'vendor/evidence_behavior.py'):
        path = root / 'reused' / name
        require(hashlib.sha256(path.read_bytes()).hexdigest() == pins['reuse:' + name]['sha256'],
                'REUSED_SOURCE_DRIFT')
    path = str(root / 'reused')
    if path not in sys.path:
        sys.path.insert(0, path)
    module = importlib.import_module('first_divergence_v1')
    require(Path(module.__file__).resolve() == root / 'reused/first_divergence_v1.py', 'REUSE_MODULE_COLLISION')
    return module.diagnose(*args, **kwargs)
