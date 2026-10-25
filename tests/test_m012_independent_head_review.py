from copy import deepcopy
from dataclasses import replace
import pytest
from openremaster.m011_signed_recovery import PinnedRecoveryTrust
from openremaster.m012_independent_head_review import (
    compare_signed_independent_heads,IndependentHeadHold,
)
from test_m011_signed_recovery import private_and_trust,make_receipt,sign,NOW,REGISTRY

def pair():
    a,ta=private_and_trust()
    b,tb=private_and_trust()
    ra=make_receipt(a)
    rb=deepcopy(ra)
    rb["authority_id"]="independent-witness-01"
    sign(b,rb)
    tb=replace(tb,authority_id="independent-witness-01")
    return a,b,ta,tb,ra,rb

def check(ta,tb,ra,rb):
    return compare_signed_independent_heads(recovery_receipt=ra,recovery_trust=ta,
        witness_receipt=rb,witness_trust=tb,recovery_authority=REGISTRY,
        witness_authority="independent-witness-01",now=NOW)

def test_matching_signed_claims_still_hold_production():
    _,_,ta,tb,ra,rb=pair()
    d=check(ta,tb,ra,rb)
    assert d["two_distinct_signatures_verified"] is True
    assert d["independent_live_current_head_verified"] is False
    assert d["native_worker_dispatch_authorized"] is False

@pytest.mark.parametrize("field",[
    "scope","operation_id","probe_id","challenge","request_sha256",
    "prior_head_sha256","candidate_head_sha256","remote_head_sha256",
    "sequence","owner_epoch","fence_generation","result",
    "remote_operation_sha256","m009_head_receipt_sha256"
])
def test_valid_resigned_witness_conflict_holds(field):
    _,b,ta,tb,ra,rb=pair()
    if isinstance(rb[field],int):
        rb[field]+=1
    elif field=="result":
        rb[field]="REJECTED"
        rb["remote_head_sha256"]=rb["prior_head_sha256"]
    elif field=="remote_head_sha256":
        rb["result"]="REJECTED"
        rb[field]=rb["prior_head_sha256"]
    else:
        rb[field]="c"*64 if field.endswith("sha256") and rb[field]!="c"*64 else ("d"*64 if field.endswith("sha256") else "different-valid-value")
    sign(b,rb)
    with pytest.raises(IndependentHeadHold):
        check(ta,tb,ra,rb)

def test_same_authority_not_independent():
    _,_,ta,tb,ra,rb=pair()
    with pytest.raises(IndependentHeadHold):
        compare_signed_independent_heads(recovery_receipt=ra,recovery_trust=ta,
            witness_receipt=rb,witness_trust=tb,recovery_authority=REGISTRY,
            witness_authority=REGISTRY,now=NOW)

def test_same_key_material_not_independent():
    a,_,ta,tb,ra,rb=pair()
    rb["authority_id"]="independent-witness-01"
    sign(a,rb)
    tb=replace(tb,public_keys=ta.public_keys)
    with pytest.raises(IndependentHeadHold):
        check(ta,tb,ra,rb)

def test_corrupt_witness_signature_holds():
    _,_,ta,tb,ra,rb=pair()
    rb["signature_b64"]="bad"
    with pytest.raises(IndependentHeadHold):
        check(ta,tb,ra,rb)


def test_same_public_key_under_different_key_ids_is_not_independent():
    a,_,ta,tb,ra,rb=pair()
    public=next(iter(ta.public_keys.values()))
    tb=replace(tb,public_keys={"witness-different-key-id":public})
    rb["key_id"]="witness-different-key-id"
    sign(a,rb)
    with pytest.raises(IndependentHeadHold):
        check(ta,tb,ra,rb)
