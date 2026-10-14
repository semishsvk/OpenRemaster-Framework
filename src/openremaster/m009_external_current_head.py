"""M009 offline external current-head contract. NEVER execution authority.

Receipt validation and a process-local replay checkpoint model only. No network,
owner register, gateway, worker, corpus, durable authority or production signer.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from threading import Lock
from datetime import timedelta

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from openremaster.m005_anchor_contract import canonical_json, sha256_json
from openremaster.m008_owner_observation_attestation import (
    verify_attestation, ObservationRejected, _instant, _now, _sha, _name,
    _int, HEX64, CHALLENGE,
)

SCHEMA = "ORF-M009.ExternalCurrentHeadReceipt.v1"
MAX_WIRE_COUNTER = 9223372036854775000
CONTEXT = b"OpenRemaster|ExternalCurrentHeadReceipt|v1\x00"
FIELDS = frozenset({
    "schema", "audience", "authority_id", "key_id", "registry_id",
    "project_id", "edition", "owner_work_scope_sha256", "challenge",
    "attestation_sha256", "previous_attestation_sha256", "sequence",
    "owner_epoch_counter", "fence_generation", "revocation_generation",
    "issued_utc", "expires_utc", "operation",
})


class HeadRejected(ValueError):
    """Fail closed; never fall back to cached authority."""


def _counter(value, label, minimum=0):
    _int(value, label, minimum=minimum)
    if value > MAX_WIRE_COUNTER:
        raise HeadRejected(label + ": exceeds wire bound")


def signing_message(receipt):
    if type(receipt) is not dict or set(receipt) != FIELDS | {"signature_b64"}:
        raise HeadRejected("receipt exact fields required")
    return CONTEXT + canonical_json({k: receipt[k] for k in FIELDS})


@dataclass(frozen=True)
class TrustSnapshot:
    """Caller-pinned lab trust; NOT independently current revocation evidence."""
    authority_id: str
    keys: dict
    revoked_key_ids: frozenset
    generation: int
    expires_utc: str


@dataclass
class SyntheticCheckpoint:
    """Single-process atomic model. Restart/rollback resistance NOT provided.

    Never reconstruct this from untrusted receipts. External implementation must
    transact head CAS, challenge consumption and revocation generation durably.
    """
    scope: tuple
    sequence: int
    epoch: int
    fence: int
    head: str
    revocation_generation: int
    consumed: set = field(default_factory=set)
    trust_content_sha256: str | None = None
    _lock: object = field(default_factory=Lock, repr=False)


def verify_current_head(*, receipt, m008_bundle, trust, checkpoint,
                        expected_challenge, now, authority_available):
    """Validate signed receipt + actual M008, then atomically update lab state.

    authority_available is a synthetic transport condition, never proof of a
    live external service. Every successful return explicitly retains HOLD.
    """
    if authority_available is not True:
        raise HeadRejected("partition: no cached-head fallback")
    if type(trust) is not TrustSnapshot or type(checkpoint) is not SyntheticCheckpoint:
        raise HeadRejected("explicit trust and checkpoint required")
    try:
        moment = _now(now)
        signing_message(receipt)
        if receipt["schema"] != SCHEMA or receipt["audience"] != "ORF-CurrentHead-ReviewOnly-v1":
            raise HeadRejected("wrong domain")
        if receipt["operation"] != "CAS_HEAD_AND_CONSUME_CHALLENGE":
            raise HeadRejected("atomic consume operation required")
        for f in ("authority_id", "key_id", "registry_id", "project_id", "edition"):
            _name(receipt[f], f)
        for f in ("owner_work_scope_sha256", "attestation_sha256", "previous_attestation_sha256"):
            _sha(receipt[f], HEX64, f)
        for f in ("sequence", "owner_epoch_counter", "fence_generation", "revocation_generation"):
            _counter(receipt[f], f, minimum=1)
        if (type(expected_challenge) is not str or
            CHALLENGE.fullmatch(expected_challenge) is None or
            receipt["challenge"] != expected_challenge):
            raise HeadRejected("challenge binding")
        _counter(trust.generation, "trust generation", minimum=1)
        if type(trust.keys) is not dict or type(trust.revoked_key_ids) is not frozenset:
            raise HeadRejected("malformed trust")
        for key_id, public_key in trust.keys.items():
            _name(key_id, "trust key id")
            if type(public_key) is not bytes or len(public_key) != 32:
                raise HeadRejected("malformed trust public key")
        for key_id in trust.revoked_key_ids:
            _name(key_id, "revoked key id")
        trust_digest = sha256_json({
            "authority_id": trust.authority_id,
            "generation": trust.generation,
            "keys": {key_id: base64.b64encode(public_key).decode("ascii")
                     for key_id, public_key in trust.keys.items()},
            "revoked_key_ids": sorted(trust.revoked_key_ids),
        })
        if moment >= _instant(trust.expires_utc, "trust expiry"):
            raise HeadRejected("stale revocation view")
        issued = _instant(receipt["issued_utc"], "receipt issued")
        expires = _instant(receipt["expires_utc"], "receipt expiry")
        if not issued <= moment < expires or not timedelta(0) < expires - issued <= timedelta(seconds=30):
            raise HeadRejected("receipt window")
        if receipt["authority_id"] != trust.authority_id:
            raise HeadRejected("authority mismatch")
        if receipt["key_id"] in trust.revoked_key_ids:
            raise HeadRejected("revoked signer")
        if receipt["revocation_generation"] != trust.generation:
            raise HeadRejected("revocation generation mismatch")
        key = trust.keys.get(receipt["key_id"])
        if type(key) is not bytes or len(key) != 32:
            raise HeadRejected("unknown signer")
        sig = receipt["signature_b64"]
        if type(sig) is not str or len(sig) > 128:
            raise HeadRejected("signature encoding")
        binary = base64.b64decode(sig, validate=True)
        if len(binary) != 64 or base64.b64encode(binary).decode("ascii") != sig:
            raise HeadRejected("noncanonical signature")
        Ed25519PublicKey.from_public_bytes(key).verify(binary, signing_message(receipt))
        if type(m008_bundle) is not dict or m008_bundle.get("now") != now:
            raise HeadRejected("same verification clock required")
        review = verify_attestation(**m008_bundle)
        a = m008_bundle["attestation"]
        if review["dispatch_authorized"] is not False:
            raise HeadRejected("M008 authority escalation")
        for f in ("authority_id", "registry_id", "project_id", "edition",
                  "owner_work_scope_sha256", "challenge", "sequence",
                  "owner_epoch_counter", "fence_generation", "previous_attestation_sha256"):
            if receipt[f] != a[f]:
                raise HeadRejected("M008 binding: " + f)
        if receipt["attestation_sha256"] != sha256_json(a):
            raise HeadRejected("M008 digest binding")
        if issued < _instant(a["issued_utc"], "M008 issued") or expires > _instant(a["expires_utc"], "M008 expires"):
            raise HeadRejected("receipt outlives or predates candidate")
        h = m008_bundle["independently_pinned_highwater"]
        with checkpoint._lock:
            if checkpoint.trust_content_sha256 is not None:
                _sha(checkpoint.trust_content_sha256, HEX64, "checkpoint trust digest")
                if (trust.generation == checkpoint.revocation_generation and
                    trust_digest != checkpoint.trust_content_sha256):
                    raise HeadRejected("trust content changed without generation advance")
            if type(checkpoint.consumed) is not set or any(
                type(challenge) is not str or CHALLENGE.fullmatch(challenge) is None
                for challenge in checkpoint.consumed
            ):
                raise HeadRejected("malformed consumed-challenge checkpoint")
            expected_scope = tuple(receipt[f] for f in (
                "authority_id", "registry_id", "project_id", "edition", "owner_work_scope_sha256"))
            if checkpoint.scope != expected_scope:
                raise HeadRejected("checkpoint scope mismatch")
            for n in (checkpoint.sequence, checkpoint.epoch, checkpoint.fence, checkpoint.revocation_generation):
                _counter(n, "checkpoint counter")
            _sha(checkpoint.head, HEX64, "checkpoint head")
            if (checkpoint.sequence != h["sequence"] or checkpoint.head != h["last_attestation_sha256"]
                or checkpoint.epoch != h["owner_epoch_counter"]):
                raise HeadRejected("checkpoint differs from candidate prior head")
            if expected_challenge in checkpoint.consumed:
                raise HeadRejected("replay: consumed challenge")
            if (receipt["sequence"] != checkpoint.sequence + 1 or
                receipt["previous_attestation_sha256"] != checkpoint.head or
                not checkpoint.epoch <= receipt["owner_epoch_counter"] <= checkpoint.epoch + 1 or
                receipt["fence_generation"] < checkpoint.fence or
                trust.generation < checkpoint.revocation_generation):
                raise HeadRejected("nonmonotonic checkpoint")
            checkpoint.consumed.add(expected_challenge)
            checkpoint.sequence = receipt["sequence"]
            checkpoint.epoch = receipt["owner_epoch_counter"]
            checkpoint.fence = receipt["fence_generation"]
            checkpoint.head = receipt["attestation_sha256"]
            checkpoint.revocation_generation = trust.generation
            checkpoint.trust_content_sha256 = trust_digest
    except (ObservationRejected, InvalidSignature, ValueError, TypeError, KeyError, binascii.Error) as exc:
        if isinstance(exc, HeadRejected):
            raise
        raise HeadRejected("invalid current-head evidence") from exc
    return {
        "status": "SYNTHETIC_CURRENT_HEAD_CONTRACT_PASS_PRODUCTION_HOLD",
        "receipt_signature_verified": True,
        "m008_signature_and_bindings_verified": True,
        "process_local_challenge_consumed": True,
        "external_current_head_independently_verified": False,
        "durable_global_challenge_consumption_verified": False,
        "current_external_revocation_verified": False,
        "rollback_resistance_verified": False,
        "dispatch_authorized": False,
        "worker_execution_authorized": False,
    }

