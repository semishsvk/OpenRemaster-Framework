from .base import ProjectSnapshot, ReadOnlyAdapter

class OpenCadaverAdapter(ReadOnlyAdapter):
    def __init__(self, revision: str) -> None:
        self.revision = revision

    def snapshot(self) -> ProjectSnapshot:
        return ProjectSnapshot("opencadaver", self.revision, {
            "mode": "read-only", "role": "discovery-corpus"
        })
