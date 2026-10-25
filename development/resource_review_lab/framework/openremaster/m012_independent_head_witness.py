"""M012 independent current-head witness cross-check — offline review only.

The witness is signed by a distinct pinned key, but both the trust view and
current-head assertion are caller-supplied. Thus even valid signatures and a
matching sequence NEVER authorize native dispatch or prove remote freshness.
"""
from __future__ import annotations
import base64
import binascii
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from openremaster.m005_anchor_contract import canonical_json,sha256_json
from openremaster.m011_signed_recovery import verify_signed_recovery_receipt,SignedRecoveryHold

SCHEMA="ORF-M012.IndependentHeadWitness.v1"
AUDIENCE="ORF-IndependentCurrentHead-ReviewOnly-v1"
CONTEXT=b"OpenRemaster|M012-IndependentHeadWitness|v1\x00"
FIELDS=frozenset(("schema","audience","witness_authority","key_id","subject_authority",
"scope","operation_id","probe_id","challenge","m011_receipt_sha256",
"observed_remote_head_sha256","observed_sequence","observed_epoch",
"observed_fence","trust_generation","issued_utc","expires_utc","signature_b64"))
HEX=re.compile(r"[0-9a-f]{64}\Z")
NAME=re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,127}\Z")
CHALLENGE=re.compile(r"[A-Za-z0-9_-]{22,128}\Z")
TIME=re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
MAX=(1<<63)-1

class WitnessHold(ValueError):
    pass

@dataclass(frozen=True)
class WitnessTrust:
    authority: str
    keys: dict
    revoked: frozenset
    generation: int
    expires_utc: str

def _name(x):
    if type(x) is not str or NAME.fullmatch(x) is None:raise WitnessHold("invalid identifier")
    return x

def _hash(x):
    if type(x) is not str or HEX.fullmatch(x) is None:raise WitnessHold("invalid hash")
    return x

def _int(x):
    if type(x) is not int or not 1<=x<MAX:raise WitnessHold("invalid positive integer")
    return x

def _time(x):
    if type(x) is not str or TIME.fullmatch(x) is None:raise WitnessHold("invalid UTC Z timestamp")
    try:return datetime.strptime(x,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:raise WitnessHold("invalid calendar timestamp") from exc

def _now(x):
    if not isinstance(x,datetime) or x.tzinfo is None or x.utcoffset() is None:raise WitnessHold("timezone-aware clock required")
    return x.astimezone(timezone.utc)

def signing_message(w):
    if type(w) is not dict or set(w)!=FIELDS:raise WitnessHold("witness field set mismatch")
    return CONTEXT+canonical_json({k:v for k,v in w.items() if k!="signature_b64"})

def verify_independent_witness(*,receipt,receipt_trust,receipt_authority,
                               witness,witness_trust,expected_witness_authority,
                               expected_challenge,expected_scope,now):
    """Review signed receipt + separate signed head, without production authority."""
    current=_now(now)
    try:
        checked=verify_signed_recovery_receipt(receipt=receipt,trust=receipt_trust,
                                                expected_authority=receipt_authority,now=now)
    except (SignedRecoveryHold,TypeError,KeyError) as exc:
        raise WitnessHold("M011 receipt signature or semantics rejected") from exc
    r=checked["verified_receipt_copy"]
    if type(witness) is not dict or set(witness)!=FIELDS:raise WitnessHold("witness field set mismatch")
    w=dict(witness)
    if w["schema"]!=SCHEMA or w["audience"]!=AUDIENCE:raise WitnessHold("wrong witness signing domain")
    for f in ("witness_authority","key_id","subject_authority","scope","operation_id","probe_id"):_name(w[f])
    for f in ("m011_receipt_sha256","observed_remote_head_sha256"):_hash(w[f])
    for f in ("observed_sequence","observed_epoch","observed_fence","trust_generation"):_int(w[f])
    if type(w["challenge"]) is not str or CHALLENGE.fullmatch(w["challenge"]) is None:raise WitnessHold("invalid witness challenge")
    if type(expected_challenge) is not str or CHALLENGE.fullmatch(expected_challenge) is None:raise WitnessHold("expected challenge invalid")
    _name(expected_witness_authority)
    _name(expected_scope)
    if type(witness_trust) is not WitnessTrust:raise WitnessHold("explicit witness trust required")
    t=witness_trust
    if type(t.keys) is not dict or type(t.revoked) is not frozenset:raise WitnessHold("invalid witness trust material")
    _name(t.authority)
    _int(t.generation)
    if current>=_time(t.expires_utc):raise WitnessHold("witness trust view expired")
    if not (t.authority==expected_witness_authority==w["witness_authority"]):raise WitnessHold("witness authority mismatch")
    if t.authority==receipt_authority:raise WitnessHold("witness not independent from receipt authority")
    if w["trust_generation"]!=t.generation:raise WitnessHold("witness trust generation mismatch")
    if w["key_id"] in t.revoked:raise WitnessHold("witness signer revoked in pinned view")
    pub=t.keys.get(w["key_id"])
    if type(pub) is not bytes or len(pub)!=32:raise WitnessHold("witness public key unavailable")
    for key_id,key in t.keys.items():
        _name(key_id)
        if type(key) is not bytes or len(key)!=32:raise WitnessHold("invalid pinned witness key")
    for key_id in t.revoked:_name(key_id)
    # Authority/key identifiers do not prove separate signing roles. Match the
    # conservative full-domain separation used by the sibling M012 head review,
    # including aliases and revoked entries retained in the pinned trust views.
    recovery_keys=receipt_trust.public_keys
    if (type(recovery_keys) is not dict or
        any(type(key) is not bytes or len(key)!=32 for key in recovery_keys.values())):
        raise WitnessHold("invalid receipt trust key material")
    if set(recovery_keys.values()) & set(t.keys.values()):
        raise WitnessHold("shared signing key material across receipt and witness trust domains")
    issued=_time(w["issued_utc"])
    expires=_time(w["expires_utc"])
    if not(issued<=current<expires and timedelta(0)<expires-issued<=timedelta(seconds=45)):
        raise WitnessHold("stale, future or overlong witness")
    if (_time(r["issued_utc"])>issued or
        issued-_time(r["issued_utc"])>timedelta(seconds=30)):
        raise WitnessHold("witness not contemporaneous with signed recovery")
    if (w["subject_authority"]!=receipt_authority or
        w["scope"]!=expected_scope or w["scope"]!=r["scope"] or
        w["operation_id"]!=r["operation_id"] or
        w["probe_id"]!=r["probe_id"] or
        w["challenge"]!=expected_challenge or
        w["challenge"]!=r["challenge"] or
        w["m011_receipt_sha256"]!=sha256_json(r)):
        raise WitnessHold("witness does not bind exact M011 operation/challenge/receipt")
    # For a COMMITTED recovery, the witness must confirm the candidate head;
    # for REJECTED it must confirm the prior head. No other outcome is accepted.
    if (w["observed_remote_head_sha256"]!=r["remote_head_sha256"] or
        w["observed_sequence"]!=(r["sequence"] if r["result"]=="COMMITTED" else r["sequence"]-1) or
        w["observed_epoch"]!=(r["owner_epoch"] if r["result"]=="COMMITTED" else max(1,r["owner_epoch"]-1)) or
        w["observed_fence"]!=(r["fence_generation"] if r["result"]=="COMMITTED" else max(1,r["fence_generation"]-1))):
        raise WitnessHold("independent witness head/epoch/fence mismatch")
    sig=w["signature_b64"]
    if type(sig) is not str or len(sig)>128:raise WitnessHold("invalid signature field")
    try:binary=base64.b64decode(sig,validate=True)
    except (ValueError,binascii.Error) as exc:raise WitnessHold("invalid base64 signature") from exc
    if len(binary)!=64 or base64.b64encode(binary).decode("ascii")!=sig:raise WitnessHold("noncanonical Ed25519 signature")
    try:Ed25519PublicKey.from_public_bytes(pub).verify(binary,signing_message(w))
    except (InvalidSignature,ValueError) as exc:raise WitnessHold("invalid witness signature") from exc
    return {
        "schema":"ORF-M012.IndependentRecoveryReviewDecision.v1",
        "status":"TWO_SIGNATURES_CROSS_BOUND_REVIEW_ONLY",
        "receipt_sha256":sha256_json(r),
        "witness_sha256":sha256_json(w),
        "m011_receipt_signature_valid":True,
        "separate_witness_signature_valid":True,
        "witness_independent_key_domain":True,
        "externally_current_highwater_verified":False,
        "witness_currentness_authenticated_from_live_service":False,
        "global_nonce_consumption_verified":False,
        "remote_cas_receipt_independently_verified":False,
        "owner_scope_epoch_mapping_verified":False,
        "native_worker_side_effect_fencing_verified":False,
        "dispatch_authorized":False,
        "worker_execution_authorized":False,
    }
