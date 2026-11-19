import json, os
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

def append_event(path, job_id, event, **fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"schema":"ExecutionJournal.Event.v1","ts":now(),"job_id":job_id,"event":event,**fields}
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return row

def read_events(path):
    path=Path(path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
