"""Review-only external highwater verification. Caller must supply trusted current anchor."""
import hashlib
import hmac
import json
from scope import Hold

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

def verify_current_anchor(local_state, anchor, trusted_current, verifier):
    """No signer or trusted source is implemented here. Fail closed without both."""
    if not callable(trusted_current) or not callable(verifier):
        raise Hold("NO_INDEPENDENT_AUTHORITY")
    current = trusted_current()
    if not isinstance(current, dict) or not isinstance(anchor, dict):
        raise Hold("INVALID_ANCHOR")
    if not verifier(current):
        raise Hold("UNTRUSTED_CURRENT_ANCHOR")
    if not hmac.compare_digest(hashlib.sha256(canonical(anchor)).digest(),
                               hashlib.sha256(canonical(current)).digest()):
        raise Hold("STALE_OR_FORGED_ANCHOR")
    if type(current.get("sequence")) is not int or current["sequence"] < 1:
        raise Hold("INVALID_SEQUENCE")
    if not isinstance(local_state, dict):
        raise Hold("INVALID_LOCAL_STATE")
    if current.get("state_sha256") != hashlib.sha256(canonical(local_state)).hexdigest():
        raise Hold("LOCAL_ROLLBACK_OR_DRIFT")
    return True
