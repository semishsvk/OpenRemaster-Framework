from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class CameraPose:
    position: tuple[float, float, float]
    rotation_deg: tuple[float, float, float]
    fov_deg: float

@dataclass(frozen=True)
class RenderConfig:
    width: int
    height: int
    lighting_profile: str
    renderer: str
    renderer_version: str

@dataclass(frozen=True)
class VisualCaptureContract:
    schema_version: str
    project_id: str
    source_revision: str
    scene_id: str
    camera_id: str
    camera: CameraPose
    render: RenderConfig
    state_digest: str
    state_id: str = ""

    def validate(self) -> None:
        if self.schema_version != "1":
            raise ValueError("unsupported visual schema")
        if self.render.width <= 0 or self.render.height <= 0:
            raise ValueError("render dimensions must be positive")
        if not 0 < self.camera.fov_deg < 180:
            raise ValueError("invalid camera fov")
        if not self.state_digest:
            raise ValueError("state digest is required")

    def canonical_json(self) -> str:
        self.validate()
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()

@dataclass(frozen=True)
class VisualArtifact:
    contract_digest: str
    image_digest: str
    format: str
    byte_size: int

    def validate(self) -> None:
        if len(self.contract_digest) != 64 or len(self.image_digest) != 64:
            raise ValueError("visual digests must be sha256 hex")
        if self.byte_size < 0:
            raise ValueError("byte_size must be non-negative")
