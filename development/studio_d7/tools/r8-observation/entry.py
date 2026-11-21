"""Fixed one-shot entry for the candidate local_dev_file_observation command."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import types

PINS = {
    "files": "8750b1cf765caa4f5e8b0338caef98c10261905d74441f9d9868ac22bc98b996",
    "producer": "1a6ff5cba8b331962677dc1851fd32defa1aeab495b2862bc5e633fa102dc085",
}


def hold(reason):
    return dict(schema="OpenRemaster.NativeFileObservation.v1", state="HOLD", reason=reason,
                read_only=True, execution_authority=False, gameplay="UNKNOWN", fidelity="UNKNOWN",
                observed_epoch_ms=time.time_ns() // 1_000_000)


def load_sibling(name):
    path = Path(__file__).with_name(name + ".py")
    if not path.is_absolute() or name in sys.modules:
        raise ValueError("Untrusted module location")
    for node in (*reversed(path.parents), path):
        if node.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError("Reparse point")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Regular file required")
    with path.open("rb") as stream:
        source = stream.read(65537)
    if len(source) > 65536 or hashlib.sha256(source).hexdigest() != PINS[name]:
        raise ValueError("Source changed")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(source, str(path), "exec"), module.__dict__)
    sys.modules[name] = module
    return module


def main():
    if (os.name != "nt" or sys.argv != ["-c"] or not sys.flags.isolated or
            not sys.flags.no_site or not sys.dont_write_bytecode):
        return hold("UNVERIFIED")
    request = sys.stdin.buffer.read(513)
    if not request or len(request) > 512:
        return hold("INVALID_REQUEST")
    def unique(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError("Duplicate request key")
        return value
    try:
        selection = json.loads(request.decode("utf-8"), object_pairs_hook=unique)
    except (ValueError, RecursionError):
        return hold("INVALID_REQUEST")
    try:
        load_sibling("files")
        return load_sibling("producer").observe(selection)
    except (ImportError, OSError, ValueError):
        return hold("UNVERIFIED")


if __name__ == "__main__":
    response = json.dumps(main(), ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if len(response) + 1 > 4096:
        response = json.dumps(hold("UNVERIFIED"), separators=(",", ":")).encode("ascii")
    sys.stdout.buffer.write(response + b"\n")
