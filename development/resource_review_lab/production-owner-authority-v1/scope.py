"""Isolated trusted scope validation; not a production owner provider."""
from dataclasses import dataclass
import hashlib
import json
import re

class Hold(Exception):
    pass

@dataclass(frozen=True)
class TrustedScope:
    project: str
    edition: str
    scenario: str
    source_sha256: str
    owner_epoch: int

    def digest(self):
        if not all(isinstance(x, str) and x.strip() for x in
                   (self.project, self.edition, self.scenario)):
            raise Hold("INVALID_SCOPE")
        if not isinstance(self.source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.source_sha256):
            raise Hold("INVALID_SOURCE_SHA")
        if type(self.owner_epoch) is not int or self.owner_epoch < 1:
            raise Hold("INVALID_EPOCH")
        data = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

def resolve(provider, request):
    """Provider must be injected by a trusted authority, never by job payload."""
    if not callable(provider) or not isinstance(request, dict):
        raise Hold("NO_TRUSTED_PROVIDER")
    scope = provider(request)
    if not isinstance(scope, TrustedScope):
        raise Hold("UNTRUSTED_SCOPE")
    scope.digest()
    for key in ("project", "edition", "scenario", "source_sha256"):
        if request.get(key) != getattr(scope, key):
            raise Hold("SCOPE_MISMATCH")
    if "owner_epoch" in request and request["owner_epoch"] != scope.owner_epoch:
        raise Hold("EPOCH_MISMATCH")
    return scope
