"""M012 independent signed-head review: no production authority, no network."""
from __future__ import annotations
import base64
from copy import deepcopy
from datetime import datetime,timezone
import secrets
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from openremaster.m005_anchor_contract import sha256_json
from openremaster.m012_independent_head_witness import (
 SCHEMA,AUDIENCE,WitnessTrust,WitnessHold,signing_message,verify_independent_witness
)
from test_m011_signed_recovery import (
 private_and_trust,make_receipt,sign as sign_receipt,REGISTRY,NOW
)

WITNESS="independent-head-witness-01"
KEY="witness-ed25519-01"

def fixture(result="COMMITTED"):
    private,receipt_trust=private_and_trust()
    receipt=make_receipt(private,result=result)
    signer=Ed25519PrivateKey.generate()
    pub=signer.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    witness_trust=WitnessTrust(WITNESS,{KEY:pub},frozenset(),2,"2026-10-14T13:05:00Z")
    w={
      "schema":SCHEMA,"audience":AUDIENCE,
      "witness_authority":WITNESS,"key_id":KEY,"subject_authority":REGISTRY,
      "scope":receipt["scope"],"operation_id":receipt["operation_id"],
      "probe_id":receipt["probe_id"],"challenge":receipt["challenge"],
      "m011_receipt_sha256":sha256_json(receipt),
      "observed_remote_head_sha256":receipt["remote_head_sha256"],
      "observed_sequence":receipt["sequence"] if result=="COMMITTED" else receipt["sequence"]-1,
      "observed_epoch":receipt["owner_epoch"] if result=="COMMITTED" else receipt["owner_epoch"]-1,
      "observed_fence":receipt["fence_generation"] if result=="COMMITTED" else receipt["fence_generation"]-1,
      "trust_generation":2,
      "issued_utc":"2026-10-14T13:00:06Z",
      "expires_utc":"2026-10-14T13:00:35Z",
      "signature_b64":"",
    }
    resign(signer,w)
    args=dict(receipt=receipt,receipt_trust=receipt_trust,receipt_authority=REGISTRY,
      witness=w,witness_trust=witness_trust,expected_witness_authority=WITNESS,
      expected_challenge=receipt["challenge"],expected_scope=receipt["scope"],now=NOW)
    return signer,args

def resign(key,w):
    w["signature_b64"]=base64.b64encode(key.sign(signing_message(w))).decode("ascii")

def review(args):
    return verify_independent_witness(**args)

@pytest.mark.parametrize("result",["COMMITTED","REJECTED"])
def test_two_valid_separate_signatures_still_never_dispatch(result):
    key,args=fixture(result)
    d=review(args)
    assert d["status"]=="TWO_SIGNATURES_CROSS_BOUND_REVIEW_ONLY"
    assert d["m011_receipt_signature_valid"] is True
    assert d["separate_witness_signature_valid"] is True
    assert d["witness_independent_key_domain"] is True
    for k,v in d.items():
        if k.endswith("_verified") and k not in ("m011_receipt_signature_valid","separate_witness_signature_valid"):
            assert v is False,k
    assert d["dispatch_authorized"] is False
    assert d["worker_execution_authorized"] is False

@pytest.mark.parametrize("field",[
 "schema","audience","witness_authority","key_id","subject_authority",
 "scope","operation_id","probe_id","challenge","m011_receipt_sha256",
 "observed_remote_head_sha256","observed_sequence","observed_epoch",
 "observed_fence","trust_generation","issued_utc","expires_utc"
])
def test_signed_field_tampering_blocks(field):
    key,args=fixture()
    w=args["witness"]
    w[field]=w[field]+1 if type(w[field]) is int else "tampered"
    with pytest.raises(WitnessHold):review(args)

@pytest.mark.parametrize("change",[
 "wrong-current-head","wrong-epoch","wrong-fence","wrong-sequence",
 "wrong-receipt-sha","wrong-probe","wrong-op","wrong-challenge",
 "wrong-scope","wrong-subject-authority","wrong-signing-audience",
 "wrong-witness-authority","wrong-witness-generation",
])
def test_resigned_but_semantically_inconsistent_witness_blocks(change):
    key,args=fixture()
    w=args["witness"]
    field,value={
     "wrong-current-head":("observed_remote_head_sha256","f"*64),
     "wrong-epoch":("observed_epoch",3),
     "wrong-fence":("observed_fence",3),
     "wrong-sequence":("observed_sequence",3),
     "wrong-receipt-sha":("m011_receipt_sha256","f"*64),
     "wrong-probe":("probe_id","different-probe"),
     "wrong-op":("operation_id","different-operation"),
     "wrong-challenge":("challenge",secrets.token_urlsafe(24)),
     "wrong-scope":("scope","another-project"),
     "wrong-subject-authority":("subject_authority","another-authority"),
     "wrong-signing-audience":("audience","ORF-NATIVE-EXECUTE"),
     "wrong-witness-authority":("witness_authority","another-witness"),
     "wrong-witness-generation":("trust_generation",3),
    }[change]
    w[field]=value
    resign(key,w)
    with pytest.raises(WitnessHold):review(args)

@pytest.mark.parametrize("change",[
 "missing-key","revoked-key","wrong-public-key","short-key",
 "same-receipt-authority","expired-trust","lower-generation",
 "bad-base64","noncanonical-base64","fake-signature","unknown-key-id",
 "naive-clock","expired-witness","future-witness","wide-witness",
 "invalid-calendar","wrong-timezone","missing-field","extra-field",
 "missing-trust","malformed-revocations"
])
def test_trust_signature_and_time_negative_cases(change):
    key,args=fixture()
    w=args["witness"]
    t=args["witness_trust"]
    if change=="missing-key":args["witness_trust"]=WitnessTrust(WITNESS,{},frozenset(),2,t.expires_utc)
    elif change=="revoked-key":args["witness_trust"]=WitnessTrust(WITNESS,t.keys,frozenset([KEY]),2,t.expires_utc)
    elif change=="wrong-public-key":
        other=Ed25519PrivateKey.generate()
        pub=other.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        args["witness_trust"]=WitnessTrust(WITNESS,{KEY:pub},frozenset(),2,t.expires_utc)
    elif change=="short-key":args["witness_trust"]=WitnessTrust(WITNESS,{KEY:b"short"},frozenset(),2,t.expires_utc)
    elif change=="same-receipt-authority":args["witness_trust"]=WitnessTrust(REGISTRY,t.keys,frozenset(),2,t.expires_utc);args["expected_witness_authority"]=REGISTRY;w["witness_authority"]=REGISTRY;resign(key,w)
    elif change=="expired-trust":args["witness_trust"]=WitnessTrust(WITNESS,t.keys,frozenset(),2,"2026-10-14T13:00:00Z")
    elif change=="lower-generation":args["witness_trust"]=WitnessTrust(WITNESS,t.keys,frozenset(),1,t.expires_utc)
    elif change=="bad-base64":w["signature_b64"]="bad!"
    elif change=="noncanonical-base64":w["signature_b64"]+="=="
    elif change=="fake-signature":resign(Ed25519PrivateKey.generate(),w)
    elif change=="unknown-key-id":w["key_id"]="unknown-key";resign(key,w)
    elif change=="naive-clock":args["now"]=NOW.replace(tzinfo=None)
    elif change=="expired-witness":w["expires_utc"]="2026-10-14T13:00:10Z";resign(key,w)
    elif change=="future-witness":w["issued_utc"]="2026-10-14T13:00:11Z";resign(key,w)
    elif change=="wide-witness":w["expires_utc"]="2026-10-14T13:05:00Z";resign(key,w)
    elif change=="invalid-calendar":w["issued_utc"]="2026-02-30T13:00:06Z";resign(key,w)
    elif change=="wrong-timezone":w["issued_utc"]="2026-10-14T15:00:06+02:00";resign(key,w)
    elif change=="missing-field":w.pop("observed_epoch")
    elif change=="extra-field":w["dispatch_authorized"]=True
    elif change=="missing-trust":args["witness_trust"]=None
    else:args["witness_trust"]=WitnessTrust(WITNESS,t.keys,["bad"],2,t.expires_utc)
    with pytest.raises(WitnessHold):review(args)

@pytest.mark.parametrize("change",["tamper-m011-signature","different-receipt","wrong-expected-challenge","wrong-expected-scope","wrong-witness-issuer"])
def test_inconsistent_m011_or_external_expectation_blocks(change):
    key,args=fixture()
    if change=="tamper-m011-signature":args["receipt"]["signature_b64"]="bad!"
    elif change=="different-receipt":
        args["receipt"]["remote_head_sha256"]="f"*64
    elif change=="wrong-expected-challenge":args["expected_challenge"]=secrets.token_urlsafe(24)
    elif change=="wrong-expected-scope":args["expected_scope"]="other-scope"
    else:args["expected_witness_authority"]="unknown-witness"
    with pytest.raises(WitnessHold):review(args)

def test_replay_with_same_claims_cannot_prove_currentness():
    key,args=fixture()
    a=review(args);b=review(args)
    assert a==b
    assert a["externally_current_highwater_verified"] is False
    assert a["global_nonce_consumption_verified"] is False

def test_two_different_witness_keys_can_sign_conflicting_heads_but_mismatch_is_hold():
    key,args=fixture()
    w=args["witness"]
    w["observed_remote_head_sha256"]="f"*64
    resign(key,w)
    with pytest.raises(WitnessHold):review(args)
