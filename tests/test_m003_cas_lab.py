"""CAS lab: SQLite transaction and crash tests; no production workers."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import shutil
import sqlite3
import threading

import pytest
from openremaster.m003_cas_lab import CASLab, Rejected, InjectedCrash, SCHEMA

NOW = datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc)


def lab(tmp_path):
    obj = CASLab(tmp_path / "lab.sqlite3")
    obj.create_namespace("project-alpha")
    return obj


def proposal(old, *, kind="ACQUIRE_PROPOSAL_ONLY", owner="o1", job="j1", attempt="a1", when=NOW, ttl=30):
    new = dict(old, store_revision=old["store_revision"] + 1)
    if kind == "ACQUIRE_PROPOSAL_ONLY":
        new.update(status="ACTIVE", owner_epoch=old["owner_epoch"] + 1,
                   job_id=job, owner_id=owner, attempt_id=attempt,
                   expires_utc=(when + timedelta(seconds=ttl)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    elif kind == "RENEW_PROPOSAL_ONLY":
        new.update(expires_utc=(when + timedelta(seconds=ttl)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    elif kind == "RELEASE_PROPOSAL_ONLY":
        new.update(status="FREE", job_id=None, owner_id=None, attempt_id=None, expires_utc=None)
    else:
        raise AssertionError("test helper unsupported kind")
    return dict(kind=kind, expected_store_revision=old["store_revision"],
                next_state=new, requires_atomic_durable_cas=True)


def apply(obj, req, *, key="first", witness=(0, 0), when=NOW, token=None, failpoint=None):
    return obj.apply("project-alpha", key, req, witness, now=when, owner_token=token, failpoint=failpoint)


def token_for(state):
    return {k: state[k] for k in ("job_id", "owner_id", "attempt_id", "owner_epoch")}


def acquire(obj, *, key="first", witness=(0, 0), when=NOW, owner="o1", job="j1", attempt="a1"):
    req = proposal(obj.snapshot("project-alpha"), when=when, owner=owner, job=job, attempt=attempt)
    return apply(obj, req, key=key, witness=witness, when=when)


def test_explicit_bootstrap_and_duplicate_blocked(tmp_path):
    db = CASLab(tmp_path / "store.db")
    with pytest.raises(Rejected, match="not initialized"):
        db.snapshot("project-alpha")
    result = db.create_namespace("project-alpha")
    assert result["dispatch_authorized"] is False
    assert db.snapshot("project-alpha")["owner_epoch"] == 0
    with pytest.raises(Rejected, match="already initialized"):
        db.create_namespace("project-alpha")


def test_acquire_durable_and_does_not_grant_dispatch(tmp_path):
    db = lab(tmp_path)
    result = acquire(db)
    assert result["status"] == "CAS_COMMITTED_LAB_ONLY"
    assert result["dispatch_authorized"] is False
    assert result["requires_external_witness_update"] is True
    assert (result["store_revision"], result["owner_epoch"]) == (1, 1)
    assert db.snapshot("project-alpha")["status"] == "ACTIVE"


def test_missing_or_wrong_witness_fails_closed(tmp_path):
    db = lab(tmp_path)
    req = proposal(db.snapshot("project-alpha"))
    for invalid in (None, [], (True, 0), (0, False), (0, 1), (2, 0)):
        with pytest.raises(Rejected):
            apply(db, req, witness=invalid)


def test_idempotent_replay_after_external_witness_advance(tmp_path):
    db = lab(tmp_path)
    req = proposal(db.snapshot("project-alpha"))
    first = apply(db, req)
    with pytest.raises(Rejected, match="WITNESS_DIVERGENCE"):
        apply(db, req)
    repeated = apply(db, req, witness=(1, 1))
    assert repeated["status"] == "REPLAYED_LAB_ONLY"
    assert repeated["dispatch_authorized"] is False
    assert repeated["request_digest"] == first["request_digest"]
    assert db.snapshot("project-alpha")["store_revision"] == 1


def test_replayed_key_with_modified_proposal_rejected(tmp_path):
    db = lab(tmp_path)
    req = proposal(db.snapshot("project-alpha"))
    apply(db, req)
    altered = copy.deepcopy(req)
    altered["next_state"]["job_id"] = "other"
    with pytest.raises(Rejected, match="IDEMPOTENCY_KEY_REUSED"):
        apply(db, altered, witness=(1, 1))


def test_two_contenders_one_cas_winner(tmp_path):
    db = lab(tmp_path)
    barrier = threading.Barrier(2)
    initial = db.snapshot("project-alpha")

    def contender(n):
        p = proposal(initial, owner="owner" + str(n), attempt="attempt" + str(n))
        barrier.wait(timeout=5)
        try:
            return apply(db, p, key="r" + str(n), witness=(0, 0))["status"]
        except Rejected as exc:
            return "REJECTED: " + str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(contender, (1, 2)))
    assert outcomes.count("CAS_COMMITTED_LAB_ONLY") == 1
    assert sum(x.startswith("REJECTED") for x in outcomes) == 1
    assert db.snapshot("project-alpha")["store_revision"] == 1


def test_renew_preserves_epoch_and_increments_store_revision(tmp_path):
    db = lab(tmp_path)
    acquire(db)
    p = proposal(db.snapshot("project-alpha"), kind="RENEW_PROPOSAL_ONLY", when=NOW + timedelta(seconds=5), ttl=60)
    receipt = apply(db, p, key="renew", witness=(1, 1), when=NOW + timedelta(seconds=5), token=token_for(db.snapshot("project-alpha")))
    assert (receipt["store_revision"], receipt["owner_epoch"]) == (2, 1)


def test_release_then_reacquire_invalidates_prior_epoch(tmp_path):
    db = lab(tmp_path)
    acquire(db)
    p = proposal(db.snapshot("project-alpha"), kind="RELEASE_PROPOSAL_ONLY")
    receipt = apply(db, p, key="release", witness=(1, 1), token=token_for(db.snapshot("project-alpha")))
    assert (receipt["store_revision"], receipt["owner_epoch"]) == (2, 1)
    acquire(db, key="new-owner", witness=(2, 1), owner="owner2", attempt="attempt2")
    state = db.snapshot("project-alpha")
    assert state["owner_epoch"] == 2 and state["store_revision"] == 3
    old_release = proposal(dict(state, store_revision=1, owner_epoch=1), kind="RELEASE_PROPOSAL_ONLY")
    with pytest.raises(Rejected):
        apply(db, old_release, key="old-owner", witness=(3, 2), token={"job_id":"j1","owner_id":"o1","attempt_id":"a1","owner_epoch":1})


def test_expired_cannot_renew_or_release(tmp_path):
    db = lab(tmp_path)
    acquire(db)
    for kind in ("RENEW_PROPOSAL_ONLY", "RELEASE_PROPOSAL_ONLY"):
        p = proposal(db.snapshot("project-alpha"), kind=kind, when=NOW + timedelta(seconds=31))
        with pytest.raises(Rejected, match="STALE_OR_EXPIRED_OWNER"):
            apply(db, p, key=kind, witness=(1, 1), when=NOW + timedelta(seconds=31), token=token_for(db.snapshot("project-alpha")))
    p = proposal(db.snapshot("project-alpha"), when=NOW + timedelta(seconds=31), owner="owner2")
    assert apply(db, p, key="replacement", witness=(1, 1), when=NOW + timedelta(seconds=31))["owner_epoch"] == 2


@pytest.mark.parametrize("tamper", ["missing", "unsupported", "unprotected", "stale", "bad_epoch", "bad_rev", "wrong_expiry", "missing_owner", "extra", "bad_type"])
def test_reject_invalid_acquire_transition(tmp_path, tamper):
    db = lab(tmp_path)
    p = proposal(db.snapshot("project-alpha"))
    if tamper == "missing": del p["next_state"]
    elif tamper == "unsupported": p["kind"] = "EXECUTE_NOW"
    elif tamper == "unprotected": p["requires_atomic_durable_cas"] = False
    elif tamper == "stale": p["expected_store_revision"] = 2
    elif tamper == "bad_epoch": p["next_state"]["owner_epoch"] = 0
    elif tamper == "bad_rev": p["next_state"]["store_revision"] = 5
    elif tamper == "wrong_expiry": p["next_state"]["expires_utc"] = "2030-01-01T00:00:00Z"
    elif tamper == "missing_owner": p["next_state"]["owner_id"] = None
    elif tamper == "extra": p["next_state"]["secret_token"] = "do not accept"
    elif tamper == "bad_type": p["expected_store_revision"] = True
    with pytest.raises(Rejected): apply(db, p)
    assert db.snapshot("project-alpha")["store_revision"] == 0


def test_crash_before_commit_rolls_back_state_and_receipt(tmp_path):
    db = lab(tmp_path)
    p = proposal(db.snapshot("project-alpha"))
    with pytest.raises(InjectedCrash, match="before"):
        apply(db, p, failpoint="before_commit")
    assert db.snapshot("project-alpha")["store_revision"] == 0
    assert apply(db, p)["status"] == "CAS_COMMITTED_LAB_ONLY"


def test_crash_after_commit_requires_witness_reconciliation(tmp_path):
    db = lab(tmp_path)
    p = proposal(db.snapshot("project-alpha"))
    with pytest.raises(InjectedCrash, match="after commit"):
        apply(db, p, failpoint="after_commit")
    assert db.snapshot("project-alpha")["store_revision"] == 1
    with pytest.raises(Rejected, match="WITNESS_DIVERGENCE"):
        apply(db, p, witness=(0, 0))
    assert apply(db, p, witness=(1, 1))["status"] == "REPLAYED_LAB_ONLY"


def test_database_restore_detected_with_independent_retained_witness(tmp_path):
    db = lab(tmp_path)
    baseline = tmp_path / "before.db"
    with sqlite3.connect(db.path) as current, sqlite3.connect(baseline) as copy_to:
        current.backup(copy_to)
    assert acquire(db)["store_revision"] == 1
    external_witness = (1, 1)  # synthetic stand-in; production anchor is NOT implemented
    shutil.copyfile(baseline, db.path)
    assert db.snapshot("project-alpha")["store_revision"] == 0
    with pytest.raises(Rejected, match="WITNESS_DIVERGENCE"):
        apply(db, proposal(db.snapshot("project-alpha")), key="new", witness=external_witness)


def test_db_payload_tamper_detected(tmp_path):
    db = lab(tmp_path)
    with sqlite3.connect(db.path) as con:
        con.execute("UPDATE states SET payload=? WHERE namespace=?", ('{"schema":"BROKEN"}', 'project-alpha'))
    with pytest.raises(Rejected): db.snapshot("project-alpha")


def test_no_namespace_injection_or_sql_execution(tmp_path):
    db = lab(tmp_path)
    with pytest.raises(Rejected): db.snapshot("bad' OR 1=1 --")
    with pytest.raises(Rejected): db.create_namespace("../path")


def test_invalid_failpoint_no_mutation(tmp_path):
    db = lab(tmp_path)
    with pytest.raises(Rejected, match="failpoint"):
        apply(db, proposal(db.snapshot("project-alpha")), failpoint="execute_worker")
    assert db.snapshot("project-alpha")["status"] == "FREE"


def test_renewal_cannot_change_owner(tmp_path):
    db = lab(tmp_path)
    acquire(db)
    p = proposal(db.snapshot("project-alpha"), kind="RENEW_PROPOSAL_ONLY", when=NOW + timedelta(seconds=1))
    p["next_state"]["owner_id"] = "other"
    with pytest.raises(Rejected, match="renew owner mismatch"):
        apply(db, p, witness=(1, 1), key="bad-renew", when=NOW + timedelta(seconds=1), token=token_for(db.snapshot("project-alpha")))


def test_no_worker_dispatch_in_any_receipt(tmp_path):
    db = lab(tmp_path)
    p = proposal(db.snapshot("project-alpha"))
    assert apply(db, p)["dispatch_authorized"] is False
    assert apply(db, p, witness=(1, 1))["dispatch_authorized"] is False


@pytest.mark.parametrize("kind", ["RENEW_PROPOSAL_ONLY", "RELEASE_PROPOSAL_ONLY"])
@pytest.mark.parametrize("fault", ["missing", "wrong-owner", "wrong-epoch", "extra-field"])
def test_renew_release_fail_closed_on_untrusted_token(tmp_path, kind, fault):
    db = lab(tmp_path)
    acquire(db)
    p = proposal(db.snapshot("project-alpha"), kind=kind, when=NOW + timedelta(seconds=1))
    token = token_for(db.snapshot("project-alpha"))
    if fault == "missing": token = None
    elif fault == "wrong-owner": token["owner_id"] = "imposter"
    elif fault == "wrong-epoch": token["owner_epoch"] = 50
    else: token["is_authorized"] = True
    with pytest.raises(Rejected):
        apply(db, p, witness=(1, 1), key="attempt", token=token, when=NOW + timedelta(seconds=1))
    assert db.snapshot("project-alpha")["store_revision"] == 1


def test_acquire_rejects_claimed_owner_token(tmp_path):
    db = lab(tmp_path)
    with pytest.raises(Rejected):
        apply(db, proposal(db.snapshot("project-alpha")), token={"owner_id":"o1"})


def test_rollback_with_forged_witness_is_not_protected_by_lab(tmp_path):
    db = lab(tmp_path)
    baseline = tmp_path / "baseline.db"
    with sqlite3.connect(db.path) as current, sqlite3.connect(baseline) as copy_to:
        current.backup(copy_to)
    assert acquire(db)["owner_epoch"] == 1
    shutil.copyfile(baseline, db.path)
    # A caller can assert a forged 0/0 witness. No signature verification exists.
    # This MUST NEVER be treated as production rollback resistance.
    result = apply(db, proposal(db.snapshot("project-alpha")), key="other", witness=(0, 0))
    assert result["status"] == "CAS_COMMITTED_LAB_ONLY"
    assert result["dispatch_authorized"] is False
