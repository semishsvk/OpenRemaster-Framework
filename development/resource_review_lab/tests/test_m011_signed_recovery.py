"""M011 signed remote recovery review lab: synthetic keys and local files only."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import os
import secrets
import sqlite3
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from openremaster.m010_durable_recovery import DurableReviewLedger, RecoveryHold
from openremaster.m011_signed_recovery import (
    AUDIENCE, CONTEXT, SCHEMA, PinnedRecoveryTrust, SignedRecoveryHold,
    SignedRecoveryJournal, signing_message, verify_signed_recovery_receipt,
)

A, B, C, D, E = ("a"*64, "b"*64, "c"*64, "d"*64, "e"*64)
NOW = datetime(2026, 10, 14, 13, 0, 10, tzinfo=timezone.utc)
REGISTRY = "review-authority-01"
SCOPE = "project-one"
OP = "operation-001"
PROBE = "recovery-probe-001"


def private_and_trust(generation=2, key_id="signer-key-001"):
    private = Ed25519PrivateKey.generate()  # ephemeral test-only
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private, PinnedRecoveryTrust(
        authority_id=REGISTRY,
        public_keys={key_id: public},
        revoked_key_ids=frozenset(),
        generation=generation,
        expires_utc="2026-10-14T13:05:00Z",
    )


def make_receipt(private, *, probe_id=PROBE, result="COMMITTED",
                 op=OP, scope=SCOPE, key_id="signer-key-001",
                 trust_generation=2, challenge=None):
    challenge = challenge or secrets.token_urlsafe(24)
    row = {
        "schema": SCHEMA, "audience": AUDIENCE, "authority_id": REGISTRY,
        "key_id": key_id, "scope": scope,
        "operation_id": op, "probe_id": probe_id,
        "challenge": challenge, "request_sha256": C,
        "prior_head_sha256": A, "candidate_head_sha256": B,
        "remote_head_sha256": B if result == "COMMITTED" else A,
        "sequence": 2, "owner_epoch": 2, "fence_generation": 2,
        "result": result, "trust_generation": trust_generation,
        "remote_operation_sha256": D, "m009_head_receipt_sha256": E,
        "issued_utc": "2026-10-14T13:00:00Z",
        "expires_utc": "2026-10-14T13:00:35Z",
        "signature_b64": "",
    }
    sign(private, row)
    return row


def sign(private, receipt):
    receipt["signature_b64"] = base64.b64encode(
        private.sign(signing_message(receipt))
    ).decode("ascii")


def initial(tmp_path):
    with DurableReviewLedger(tmp_path) as l:
        l.initialize(SCOPE,1,1,1,A)
        l.prepare(op=OP,scope=SCOPE,challenge="original-job-001",
                  prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2)


def planned(tmp_path, *, trust_generation=2):
    initial(tmp_path)
    private, trust = private_and_trust(generation=trust_generation)
    receipt = make_receipt(private,trust_generation=trust_generation)
    with SignedRecoveryJournal(tmp_path) as j:
        j.plan_probe(op=OP,probe_id=PROBE,
                     challenge=receipt["challenge"], request_sha256=C,
                     expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=trust_generation)
    return private, trust, receipt


def verify_only(receipt, trust= None, key=None, now=NOW):
    if trust is None:
        private, trust = private_and_trust()
        if key is not None:
            trust = key
    return verify_signed_recovery_receipt(
        receipt=receipt, trust=trust,
        expected_authority=REGISTRY, now=now,
    )


def test_initial_m010_parent_operation_is_not_dispatch_authority(tmp_path):
    initial(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.status()
        assert s["schema"]=="ORF-M011.LocalSignedRecoveryJournal.v1"
        assert s["operations"]==[(OP,"PREPARED",None)]
        assert s["probes"]==[]
        assert s["external_current_head_verified"] is False
        assert s["native_worker_dispatch_authorized"] is False


def test_prepare_probe_marks_operation_unknown_atomically(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.status()
        assert s["operations"]==[(OP,"UNKNOWN",None)]
        assert s["probes"]==[(PROBE,OP,"PENDING",None)]
        assert s["heads"][0][-1]==A
        assert s["worker_execution_authorized"] is False


def test_signed_commit_and_reopen_locally_recorded_only(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.apply_signed_result(receipt=receipt,trust=trust,
                  expected_authority=REGISTRY,now=NOW)
        assert s["heads"] == [(SCOPE,2,2,2,B)]
        assert s["operations"][0][1] == "COMMIT_RECORDED_REVIEW_ONLY"
        assert s["probes"][0][2] == "SIGNED_COMMIT_RECORDED_REVIEW_ONLY"
        assert s["probes"][0][3] == s["operations"][0][2]
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.status()
        assert s["heads"][0][-1]==B
        assert s["external_current_head_verified"] is False
        assert s["remote_commit_signature_is_authoritative_for_native_jobs"] is False
        assert s["native_worker_dispatch_authorized"] is False


def test_signed_rejection_preserves_prior_local_head(tmp_path):
    initial(tmp_path)
    private,trust=private_and_trust()
    receipt=make_receipt(private,result="REJECTED")
    with SignedRecoveryJournal(tmp_path) as j:
        j.plan_probe(op=OP,probe_id=PROBE,challenge=receipt["challenge"],
                     request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=2)
        s=j.apply_signed_result(receipt=receipt,trust=trust,
                                expected_authority=REGISTRY,now=NOW)
        assert s["heads"][0][-1] == A
        assert s["operations"][0][1] == "REJECTED"
        assert s["probes"][0][2] == "SIGNED_REJECTION_RECORDED_REVIEW_ONLY"
    with SignedRecoveryJournal(tmp_path) as j:
        assert j.status()["heads"][0][-1] == A


def test_signed_bytes_are_validated_but_current_authority_remains_false(tmp_path):
    private,trust,receipt=planned(tmp_path)
    s=verify_signed_recovery_receipt(
        receipt=receipt,trust=trust,expected_authority=REGISTRY,now=NOW)
    assert s["receipt_signature_valid"] is True
    assert s["status"]=="SIGNED_RECOVERY_CLAIM_REVIEW_ONLY"
    assert s["external_current_head_verified"] is False
    assert s["remote_nonce_consumption_verified"] is False
    assert s["native_worker_dispatch_authorized"] is False


def test_timeout_or_partition_cannot_guess_commit(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        j.mark_partition(op=OP)
        j.mark_partition(op=OP)
        s=j.status()
        assert s["heads"][0][-1] == A
        assert s["operations"][0][1]=="UNKNOWN"
        assert s["probes"][0][2]=="PENDING"
        assert s["worker_execution_authorized"] is False


def test_signature_confirms_result_bytes_not_current_external_highwater(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.apply_signed_result(receipt=receipt,trust=trust,
                                 expected_authority=REGISTRY,now=NOW)
        for k in ("external_current_head_verified",
                  "remote_commit_signature_is_authoritative_for_native_jobs",
                  "remote_challenge_single_use_verified",
                  "local_rollback_resistance_proven",
                  "native_worker_dispatch_authorized"):
            assert s[k] is False, k


@pytest.mark.parametrize("field", [
    "schema","audience","authority_id","key_id","scope","operation_id",
    "probe_id","challenge","request_sha256","prior_head_sha256",
    "candidate_head_sha256","remote_head_sha256","sequence",
    "owner_epoch","fence_generation","result","trust_generation",
    "remote_operation_sha256","m009_head_receipt_sha256","issued_utc","expires_utc"
])
def test_any_unsigned_mutation_blocks_before_db_write(tmp_path,field):
    private,trust,receipt=planned(tmp_path)
    if isinstance(receipt[field],int):
        receipt[field]+=1
    else:
        receipt[field]="tampered"
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                 expected_authority=REGISTRY,now=NOW)
        assert j.status()["operations"][0][1]=="UNKNOWN"


@pytest.mark.parametrize("wrong", [
    "no-trust","not-explicit-trust","revoked","wrong-key","short-key",
    "wrong-generation","wrong-authority","trust-expired","wrong-key-id",
    "invalid-base64","noncanonical-sig","wrong-signature"
])
def test_invalid_signer_or_trust_fails_closed(tmp_path, wrong):
    private,trust,receipt=planned(tmp_path)
    if wrong=="no-trust":
        trust=None
    elif wrong=="not-explicit-trust":
        trust={"authority_id":REGISTRY}
    elif wrong=="revoked":
        trust=PinnedRecoveryTrust(REGISTRY,trust.public_keys,
                    frozenset(("signer-key-001",)),2,trust.expires_utc)
    elif wrong=="wrong-key":
        other=Ed25519PrivateKey.generate()
        bad_pub=other.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        trust=PinnedRecoveryTrust(REGISTRY,{"signer-key-001":bad_pub},
                                  frozenset(),2,trust.expires_utc)
    elif wrong=="short-key":
        trust=PinnedRecoveryTrust(REGISTRY,{"signer-key-001":b"bad"},
                                  frozenset(),2,trust.expires_utc)
    elif wrong=="wrong-generation":
        trust=PinnedRecoveryTrust(REGISTRY,trust.public_keys,frozenset(),3,
                                  trust.expires_utc)
    elif wrong=="wrong-authority":
        trust=PinnedRecoveryTrust("other-authority",trust.public_keys,
                                  frozenset(),2,trust.expires_utc)
    elif wrong=="trust-expired":
        trust=PinnedRecoveryTrust(REGISTRY,trust.public_keys,
                                  frozenset(),2,"2026-10-14T13:00:01Z")
    elif wrong=="wrong-key-id":
        receipt["key_id"]="untrusted-key-001"
        sign(private,receipt)
    elif wrong=="invalid-base64":
        receipt["signature_b64"]="%%%invalid"
    elif wrong=="noncanonical-sig":
        receipt["signature_b64"]+="=="
    else:
        fake=Ed25519PrivateKey.generate()
        sign(fake,receipt)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                 expected_authority=REGISTRY,now=NOW)
        assert j.status()["heads"][0][-1]==A


@pytest.mark.parametrize("tamper", [
    "wrong-operation","wrong-probe","wrong-challenge","wrong-query-hash",
    "wrong-scope","wrong-prior","wrong-candidate",
    "wrong-sequence","wrong-epoch","wrong-fence"
])
def test_resigned_conflicting_remote_result_does_not_reconcile(tmp_path,tamper):
    private,trust,receipt=planned(tmp_path)
    key={
        "wrong-operation":"operation-unknown",
        "wrong-probe":"recovery-probe-other",
        "wrong-challenge":secrets.token_urlsafe(24),
        "wrong-query-hash":D,
        "wrong-scope":"other-project",
        "wrong-prior":D,
        "wrong-candidate":D,
        "wrong-sequence":3,
        "wrong-epoch":3,
        "wrong-fence":3,
    }[tamper]
    field={
        "wrong-operation":"operation_id","wrong-probe":"probe_id",
        "wrong-challenge":"challenge","wrong-query-hash":"request_sha256",
        "wrong-scope":"scope","wrong-prior":"prior_head_sha256",
        "wrong-candidate":"candidate_head_sha256",
        "wrong-sequence":"sequence","wrong-epoch":"owner_epoch",
        "wrong-fence":"fence_generation",
    }[tamper]
    receipt[field]=key
    if tamper=="wrong-candidate":
        receipt["remote_head_sha256"]=D
    sign(private,receipt)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                  expected_authority=REGISTRY,now=NOW)
        assert j.status()["heads"][0][-1]==A


@pytest.mark.parametrize("wrong", [
    "bool-sequence","over-limit","wrong-remote-head",
    "bad-result","unknown-result","expired","future",
    "too-wide-window","wrong-utc-zone","invalid-calendar"
])
def test_malformed_signed_receipt_even_if_resigned_blocks(tmp_path,wrong):
    private,trust,receipt=planned(tmp_path)
    if wrong=="bool-sequence":
        receipt["sequence"]=True
    elif wrong=="over-limit":
        receipt["fence_generation"]=2**63
    elif wrong=="wrong-remote-head":
        receipt["remote_head_sha256"]=C
    elif wrong=="bad-result":
        receipt["result"]="SYNTHETIC_PASS"
    elif wrong=="unknown-result":
        receipt["result"]="UNKNOWN"
    elif wrong=="expired":
        receipt["expires_utc"]="2026-10-14T13:00:10Z"
    elif wrong=="future":
        receipt["issued_utc"]="2026-10-14T13:00:11Z"
    elif wrong=="too-wide-window":
        receipt["expires_utc"]="2026-10-14T13:05:00Z"
    elif wrong=="wrong-utc-zone":
        receipt["issued_utc"]="2026-10-14T15:00:00+02:00"
    else:
        receipt["expires_utc"]="2026-02-30T13:00:35Z"
    sign(private,receipt)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                  expected_authority=REGISTRY,now=NOW)
        assert j.status()["operations"][0][1]=="UNKNOWN"


def test_plan_requires_real_m010_prepared_or_unknown_op(tmp_path):
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold):
            j.plan_probe(op=OP,probe_id=PROBE,challenge=secrets.token_urlsafe(24),
                         request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=2)
        assert j.status()["probes"]==[]


def test_plan_rejects_duplicate_inquiry_and_keeps_head(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold):
            j.plan_probe(op=OP,probe_id="recovery-probe-002",
                         challenge=secrets.token_urlsafe(24),
                         request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=2)
        assert j.status()["probes"][0][2]=="PENDING"
        assert j.status()["heads"][0][-1]==A


def test_repeated_signed_result_never_advances_twice(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        j.apply_signed_result(receipt=receipt,trust=trust,
                              expected_authority=REGISTRY,now=NOW)
        with pytest.raises(SignedRecoveryHold,match="replay"):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                  expected_authority=REGISTRY,now=NOW)
        assert j.status()["heads"][0][-1]==B


def test_wrong_local_head_must_refuse_signed_remote_confirmation(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        j.db.execute("UPDATE head SET digest=? WHERE scope=?", (D,SCOPE))
        with pytest.raises(SignedRecoveryHold,match="local head changed"):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                  expected_authority=REGISTRY,now=NOW)
        assert j.status()["heads"][0][-1]==D


def test_caller_mutating_receipt_after_validation_does_not_modify_stored_digest(tmp_path):
    private,trust,receipt=planned(tmp_path)
    original=deepcopy(receipt)
    with SignedRecoveryJournal(tmp_path) as j:
        j.apply_signed_result(receipt=receipt,trust=trust,
                              expected_authority=REGISTRY,now=NOW)
        signed_sha=j.status()["probes"][0][3]
        receipt["result"]="REJECTED"
        receipt["remote_head_sha256"]=A
        assert signed_sha == j.status()["probes"][0][3]
        assert signed_sha != "f"*64


def test_signed_result_after_partition_can_still_be_reviewed(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        j.mark_partition(op=OP)
        assert j.status()["operations"][0][1]=="UNKNOWN"
        s=j.apply_signed_result(receipt=receipt,trust=trust,
                                 expected_authority=REGISTRY,now=NOW)
        assert s["heads"][0][-1]==B
        assert s["native_worker_dispatch_authorized"] is False


@pytest.mark.parametrize("point,final",[
    ("BEFORE_PROBE_COMMIT",False), ("AFTER_PROBE_COMMIT",True)
])
def test_probe_exception_failpoints_atomic(tmp_path,point,final):
    initial(tmp_path)
    nonce=secrets.token_urlsafe(24)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold,match=point):
            j.plan_probe(op=OP,probe_id=PROBE,challenge=nonce,
                         request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=2,
                         failpoint=point)
    with SignedRecoveryJournal(tmp_path) as j:
        st=j.status()
        assert len(st["probes"])==(1 if final else 0)
        assert st["operations"][0][1]==("UNKNOWN" if final else "PREPARED")


@pytest.mark.parametrize("point,final",[
    ("BEFORE_SIGNED_RESULT_COMMIT",False), ("AFTER_SIGNED_RESULT_COMMIT",True)
])
def test_signed_reconcile_exception_failpoints_atomic(tmp_path,point,final):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold,match=point):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                  expected_authority=REGISTRY,now=NOW,
                                  failpoint=point)
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.status()
        assert s["heads"][0][-1]==(B if final else A)
        assert s["probes"][0][2]==(
            "SIGNED_COMMIT_RECORDED_REVIEW_ONLY" if final else "PENDING"
        )
        assert j.db.execute("PRAGMA quick_check").fetchone()[0]=="ok"


@pytest.mark.parametrize("point,kind,expected,committed",[
    ("BEFORE_PROBE_COMMIT","plan",71,False),
    ("AFTER_PROBE_COMMIT","plan",72,True),
    ("BEFORE_SIGNED_RESULT_COMMIT","signed",73,False),
    ("AFTER_SIGNED_RESULT_COMMIT","signed",74,True),
])
def test_real_child_process_termination_and_reopen(tmp_path,point,kind,expected,committed):
    initial(tmp_path)
    private,trust=private_and_trust()
    receipt=make_receipt(private)
    if kind=="signed":
        with SignedRecoveryJournal(tmp_path) as j:
            j.plan_probe(op=OP,probe_id=PROBE,challenge=receipt["challenge"],
                         request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=2)
    data={
        "receipt":receipt,
        "public":base64.b64encode(trust.public_keys["signer-key-001"]).decode("ascii"),
        "trust_expires_utc":trust.expires_utc,
    }
    fixture=tmp_path/"signed-fixture.json"
    fixture.write_text(json.dumps(data),encoding="utf-8")
    code=r'''
import base64,json,os,sys
import openremaster.m011_signed_recovery as module
from openremaster.m011_signed_recovery import SignedRecoveryJournal,PinnedRecoveryTrust
from datetime import datetime,timezone
D,phase,failpoint,exitcode,fixture=sys.argv[1:]
args=json.load(open(fixture,encoding='utf-8'))
receipt=args['receipt']
trust=PinnedRecoveryTrust('review-authority-01',
 {'signer-key-001':base64.b64decode(args['public'])},frozenset(),2,args['trust_expires_utc'])
module._failure=lambda selected,at:os._exit(int(exitcode)) if selected==at else None
with SignedRecoveryJournal(D) as j:
 if phase=='plan':
  j.plan_probe(op='operation-001',probe_id='recovery-probe-001',
   challenge=receipt['challenge'],request_sha256='c'*64,
   expected_remote_operation_sha256='d'*64,
   expected_m009_head_receipt_sha256='e'*64,
   trust_generation=2,failpoint=failpoint)
 else:
  j.apply_signed_result(receipt=receipt,trust=trust,
   expected_authority='review-authority-01',
   now=datetime(2026,10,14,13,0,10,tzinfo=timezone.utc),failpoint=failpoint)
sys.exit(99)
'''
    env=dict(os.environ)
    env["PYTHONPATH"]=str(Path(__file__).resolve().parents[1]/"src")
    env["PYTHONDONTWRITEBYTECODE"]="1"
    proc=subprocess.run(
        [sys.executable,"-B","-c",code,str(tmp_path),kind,point,
         str(expected),str(fixture)],
        env=env,timeout=16,capture_output=True,text=True,
    )
    assert proc.returncode==expected, (proc.returncode,proc.stdout,proc.stderr)
    with SignedRecoveryJournal(tmp_path) as j:
        s=j.status()
        assert j.db.execute("PRAGMA quick_check").fetchone()[0]=="ok"
        if kind=="plan":
            assert len(s["probes"])==(1 if committed else 0)
            assert s["heads"][0][-1]==A
            assert s["operations"][0][1]==("UNKNOWN" if committed else "PREPARED")
        else:
            assert s["heads"][0][-1]==(B if committed else A)
            assert s["operations"][0][1]==(
                "COMMIT_RECORDED_REVIEW_ONLY" if committed else "UNKNOWN"
            )
        assert s["native_worker_dispatch_authorized"] is False


def test_two_connection_signed_result_race_single_winner(tmp_path):
    private,trust,receipt=planned(tmp_path)
    def contend(_):
        try:
            with SignedRecoveryJournal(tmp_path) as j:
                j.apply_signed_result(receipt=receipt,trust=trust,
                                      expected_authority=REGISTRY,now=NOW)
            return "WIN"
        except SignedRecoveryHold:
            return "HOLD"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(contend,range(2)))
    assert sorted(results)==["HOLD","WIN"]
    with SignedRecoveryJournal(tmp_path) as j:
        assert j.status()["heads"][0][-1]==B


def test_local_generation_rollback_and_key_id_rebind_blocked(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        j.apply_signed_result(receipt=receipt,trust=trust,
                              expected_authority=REGISTRY,now=NOW)
        j.ledger.initialize("project-two",1,1,1,A)
        j.ledger.prepare(op="operation-002",scope="project-two",
             challenge="original-job-002",prior_digest=A,candidate_digest=B,
             sequence=2,epoch=2,fence=2)
        other_probe="recovery-probe-002"
        second=make_receipt(private,probe_id=other_probe,op="operation-002",
                            scope="project-two",challenge=secrets.token_urlsafe(24))
        j.plan_probe(op="operation-002",probe_id=other_probe,
               challenge=second["challenge"],request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=1)
        lower=PinnedRecoveryTrust(REGISTRY,trust.public_keys,frozenset(),
                                  1,trust.expires_utc)
        second["trust_generation"]=1
        sign(private,second)
        with pytest.raises(SignedRecoveryHold,match="trust generation"):
            j.apply_signed_result(receipt=second,trust=lower,
                                  expected_authority=REGISTRY,now=NOW)
        alt,alt_trust=private_and_trust()
        rebound=PinnedRecoveryTrust(REGISTRY,alt_trust.public_keys,
                                   frozenset(),2,trust.expires_utc)
        second["trust_generation"]=2
        sign(alt,second)
        with pytest.raises(SignedRecoveryHold,match="rebound"):
            j.apply_signed_result(receipt=second,trust=rebound,
                                  expected_authority=REGISTRY,now=NOW)
        assert j.status()["operations"][1][1]=="UNKNOWN"


def test_revocation_tombstones_cannot_be_removed_by_later_trust_view(tmp_path):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        j.apply_signed_result(receipt=receipt,trust=trust,
                              expected_authority=REGISTRY,now=NOW)
        another, another_trust = private_and_trust(
            generation=3,key_id="signer-key-002"
        )
        j.ledger.initialize("project-two",1,1,1,A)
        j.ledger.prepare(op="operation-002",scope="project-two",
           challenge="original-job-002",prior_digest=A,candidate_digest=B,
           sequence=2,epoch=2,fence=2)
        probe2="recovery-probe-002"
        signed2=make_receipt(another,probe_id=probe2,op="operation-002",
                 scope="project-two",key_id="signer-key-002",
                 trust_generation=3)
        j.plan_probe(op="operation-002",probe_id=probe2,
             challenge=signed2["challenge"],request_sha256=C,
             expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=3)
        current= PinnedRecoveryTrust(
            REGISTRY, {**trust.public_keys, **another_trust.public_keys},
            frozenset(("signer-key-001",)),3,trust.expires_utc
        )
        j.apply_signed_result(receipt=signed2,trust=current,
                  expected_authority=REGISTRY,now=NOW)
        j.ledger.initialize("project-three",1,1,1,A)
        j.ledger.prepare(op="operation-003",scope="project-three",
            challenge="original-job-003",prior_digest=A,candidate_digest=B,
            sequence=2,epoch=2,fence=2)
        probe3="recovery-probe-003"
        signed3=make_receipt(another,probe_id=probe3,op="operation-003",
                  scope="project-three",key_id="signer-key-002",trust_generation=4)
        j.plan_probe(op="operation-003",probe_id=probe3,
           challenge=signed3["challenge"],request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=4)
        newer=PinnedRecoveryTrust(
            REGISTRY,{**trust.public_keys,**another_trust.public_keys},
            frozenset(),4,trust.expires_utc
        )
        with pytest.raises(SignedRecoveryHold,match="tombstone"):
            j.apply_signed_result(receipt=signed3,trust=newer,
                         expected_authority=REGISTRY,now=NOW)
        assert j.status()["probes"][-1][2]=="PENDING"


def test_privileged_whole_database_rollback_not_detectable(tmp_path):
    with DurableReviewLedger(tmp_path) as l:
        l.initialize(SCOPE,1,1,1,A)
        # checkpoint source with no open operation as valid baseline
    original=(tmp_path/"m010-review-only.sqlite3").read_bytes()
    with SignedRecoveryJournal(tmp_path) as j:
        j.ledger.prepare(op=OP,scope=SCOPE,challenge="original-job-001",
             prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2)
        key,trust=private_and_trust()
        receipt=make_receipt(key)
        j.plan_probe(op=OP,probe_id=PROBE,challenge=receipt["challenge"],
             request_sha256=C,expected_remote_operation_sha256=D,
                     expected_m009_head_receipt_sha256=E,
                     trust_generation=2)
        j.apply_signed_result(receipt=receipt,trust=trust,
             expected_authority=REGISTRY,now=NOW)
        assert j.status()["heads"][0][-1]==B
    (tmp_path/"m010-review-only.sqlite3").write_bytes(original)
    with SignedRecoveryJournal(tmp_path) as j:
        result=j.status()
        assert result["heads"][0][-1]==A
        assert result["local_rollback_resistance_proven"] is False
        assert result["external_current_head_verified"] is False


@pytest.mark.parametrize("point",["UNKNOWN_ERROR","AFTER_NATIVE_WORKER"])
def test_invalid_injected_failure_points_never_mutate(tmp_path,point):
    private,trust,receipt=planned(tmp_path)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold,match="invalid test-only"):
            j.apply_signed_result(receipt=receipt,trust=trust,
                                  expected_authority=REGISTRY,now=NOW,
                                  failpoint=point)
        assert j.status()["heads"][0][-1]==A


@pytest.mark.parametrize("field", ["remote_operation_sha256", "m009_head_receipt_sha256"])
def test_resigned_unplanned_remote_provenance_hash_rejected(tmp_path,field):
    private,trust,receipt=planned(tmp_path)
    receipt[field]="f"*64
    sign(private,receipt)
    with SignedRecoveryJournal(tmp_path) as j:
        with pytest.raises(SignedRecoveryHold,match="not bound to durable inquiry"):
            j.apply_signed_result(receipt=receipt,trust=trust,
                  expected_authority=REGISTRY,now=NOW)
        assert j.status()["external_current_head_verified"] is False
        assert j.status()["heads"][0][-1]==A
