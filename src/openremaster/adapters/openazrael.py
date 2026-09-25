from .base import ProjectSnapshot, ReadOnlyAdapter

class OpenAzraelAdapter(ReadOnlyAdapter):
    def __init__(self, revision: str) -> None:
        self.revision = revision

    def snapshot(self) -> ProjectSnapshot:
        return ProjectSnapshot("openazrael", self.revision, {
            "mode": "read-only", "role": "stability-corpus"
        })
