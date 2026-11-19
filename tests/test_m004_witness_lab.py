"""Synthetic M004 tests: two disposable SQLite stores, no production services."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta, timezone
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import threading

import pytest

from openremaster.m004_witness_lab import (
    WitnessEmulator, TwoStoreCoordinatorLab, WitnessBlocked, SimulatedCrash,
    digest, canonical_json,
)

NOW = datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc)
KEY = b"a test-only 32-byte witness HMAC key, NOT secret"
NS = "project-alpha"


def genesis():
    return {
        "schema": "ORCH-M002.Structural.v0.OwnerSnapshot", "store_revision": 0,
        "owner_epoch": 0, "status": "FREE", "job_id": None, "owner_id": None,
        "attempt_id": None, "expires_utc": None,
    }


def acquire_proposal(old, *, job="j1", owner="o1", attempt="a1", now=NOW):
    after = dict(old, store_revision=old["store_revision"] + 1,
                 owner_epoch=old["owner_epoch"] + 1, status="ACTIVE",
                 job_id=job, owner_id=owner, attempt_id=attempt,
                 expires_utc=(now + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return {"kind": "ACQUIRE_PROPOSAL_ONLY", "expected_store_revision": old["store_revision"],
            "next_state": after, "requires_atomic_durable_cas": True}


class DisposableOwnerAdapter:
    """Standalone SQLite CAS fixture with the same interface as M003 CASLab.

    This is a test fixture, NOT a substitute for actual M003 integration review.
    """
    def __init__(self, path):
        self.path = Path(path)
        with closing(self._connect()) as db:
            db.execute("CREATE TABLE IF NOT EXISTS states (namespace TEXT PRIMARY KEY, revision INTEGER, epoch INTEGER, payload TEXT)")

    def _connect(self):
        return sqlite3.connect(self.path, timeout=5, isolation_level=None)

    def create_namespace(self, namespace):
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO states VALUES (?,?,?,?)", (namespace, 0, 0, canonical_json(genesis())))
            db.commit()

    def snapshot(self, namespace):
        with closing(self._connect()) as db:
            row = db.execute("SELECT revision,epoch,payload FROM states WHERE namespace=?", (namespace,)).fetchone()
        if row is None:
            raise WitnessBlocked("owner namespace not initialized")
        state = json.loads(row[2])
        if (state["store_revision"], state["owner_epoch"]) != (row[0], row[1]):
            raise WitnessBlocked("owner state inconsistent")
        return state

    def apply(self, namespace, key, proposal, witness, *, now, owner_token=None):
        with closing(self._connect()) as db:
            try:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT revision,epoch,payload FROM states WHERE namespace=?", (namespace,)).fetchone()
                before = json.loads(row[2]); after = proposal["next_state"]
                if (row[0], row[1]) != witness:
                    raise WitnessBlocked("owner witness mismatch")
                if (proposal["kind"] != "ACQUIRE_PROPOSAL_ONLY" or owner_token is not None
                        or proposal["requires_atomic_durable_cas"] is not True
                        or before["status"] != "FREE"
                        or after["store_revision"] != before["store_revision"] + 1
                        or after["owner_epoch"] != before["owner_epoch"] + 1):
                    raise WitnessBlocked("invalid owner CAS proposal")
                changed = db.execute("UPDATE states SET revision=?,epoch=?,payload=? WHERE namespace=? AND revision=? AND epoch=?",
                                     (after["store_revision"], after["owner_epoch"], canonical_json(after),
                                      namespace, witness[0], witness[1]))
                if changed.rowcount != 1:
                    raise WitnessBlocked("owner CAS lost")
                db.commit()
                return {"status": "CAS_COMMITTED_LAB_ONLY", "dispatch_authorized": False,
                        "store_revision": after["store_revision"], "owner_epoch": after["owner_epoch"]}
            except BaseException:
                db.rollback()
                raise


def setup_lab(tmp_path, *, key=KEY):
    owner = DisposableOwnerAdapter(tmp_path / "owner.sqlite3")
    owner.create_namespace(NS)
    witness = WitnessEmulator(tmp_path / "witness.sqlite3", test_key=key)
    witness.initialize(NS, owner.snapshot(NS))
    return owner, witness, TwoStoreCoordinatorLab(owner, witness)


def advance(coordinator, owner, *, failpoint=None, key="req1"):
    return coordinator.apply(NS, key, acquire_proposal(owner.snapshot(NS)), now=NOW,
                             failpoint=failpoint)


def test_two_store_happy_path_never_authorizes(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    result = advance(coordinator, owner)
    assert result["status"] == "TWO_STORE_LAB_ONLY"
    assert result["dispatch_authorized"] is False
    assert result["owner_result"]["dispatch_authorized"] is False
    assert result["witness_result"]["dispatch_authorized"] is False
    assert witness.snapshot(NS)["pending"] is None
    assert witness.snapshot(NS)["revision"] == 1
    assert coordinator.recover(NS)["status"] == "STABLE_LAB_ONLY"


def test_after_prepare_crash_blocks_without_auto_abort(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    with pytest.raises(SimulatedCrash, match="after witness prepare"):
        advance(coordinator, owner, failpoint="after_prepare")
    assert witness.snapshot(NS)["pending"] is not None
    assert owner.snapshot(NS)["store_revision"] == 0
    assert coordinator.recover(NS)["status"] == "PENDING_WITH_OLD_DB_BLOCKED"
    with pytest.raises(WitnessBlocked, match="pending witness"):
        advance(coordinator, owner, key="req2")


def test_after_owner_commit_crash_recovers_forward_only(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    with pytest.raises(SimulatedCrash, match="after DB commit"):
        advance(coordinator, owner, failpoint="after_owner_commit")
    assert owner.snapshot(NS)["store_revision"] == 1
    assert witness.snapshot(NS)["revision"] == 0
    assert witness.snapshot(NS)["pending"] is not None
    result = coordinator.recover(NS)
    assert result["status"] == "FORWARD_COMMITTED_LAB_ONLY"
    assert result["dispatch_authorized"] is False
    assert coordinator.recover(NS)["status"] == "STABLE_LAB_ONLY"


def test_after_witness_commit_crash_recovery_is_stable(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    with pytest.raises(SimulatedCrash, match="after witness commit"):
        advance(coordinator, owner, failpoint="after_witness_commit")
    assert coordinator.recover(NS)["status"] == "STABLE_LAB_ONLY"


def test_witness_prepared_intent_blocks_second_prepare(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    witness.prepare(NS, "req1", before, acquire_proposal(before)["next_state"])
    with pytest.raises(WitnessBlocked, match="PENDING_RECONCILIATION"):
        witness.prepare(NS, "req2", before, acquire_proposal(before)["next_state"])


def test_ticket_authenticity_rejects_tampered_mac(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    ticket = witness.prepare(NS, "req1", before, acquire_proposal(before)["next_state"])
    mutated = copy.deepcopy(ticket); mutated["mac_sha256"] = "0" * 64
    with pytest.raises(WitnessBlocked, match="invalid ticket MAC"):
        witness.finalize(NS, mutated, before)


def test_ticket_replay_after_finalization_rejected(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    proposal = acquire_proposal(before)
    ticket = witness.prepare(NS, "req1", before, proposal["next_state"])
    owner.apply(NS, "req1", proposal, (0, 0), now=NOW)
    witness.finalize(NS, ticket, owner.snapshot(NS))
    with pytest.raises(WitnessBlocked, match="does not match"):
        witness.finalize(NS, ticket, owner.snapshot(NS))


def test_finalize_requires_target_database_not_before(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    ticket = witness.prepare(NS, "req1", before, acquire_proposal(before)["next_state"])
    with pytest.raises(WitnessBlocked, match="DB_NOT_AT_PREPARED_TARGET"):
        witness.finalize(NS, ticket, before)
    assert witness.snapshot(NS)["pending"] is not None


def test_owner_rollback_detected_by_independent_witness_db(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    snapshot_file = tmp_path / "owner_before.sqlite3"
    shutil.copyfile(owner.path, snapshot_file)
    advance(coordinator, owner)
    shutil.copyfile(snapshot_file, owner.path)
    with pytest.raises(WitnessBlocked, match="STABLE_DB_WITNESS_DIVERGENCE"):
        coordinator.recover(NS)


def test_witness_rollback_detected_by_owner_db(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    snapshot_file = tmp_path / "witness_before.sqlite3"
    shutil.copyfile(witness.path, snapshot_file)
    advance(coordinator, owner)
    shutil.copyfile(snapshot_file, witness.path)
    with pytest.raises(WitnessBlocked, match="STABLE_DB_WITNESS_DIVERGENCE"):
        coordinator.recover(NS)


def test_both_databases_rolled_back_cannot_be_detected(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before_owner = tmp_path / "owner_prior.sqlite3"
    before_witness = tmp_path / "witness_prior.sqlite3"
    shutil.copyfile(owner.path, before_owner)
    shutil.copyfile(witness.path, before_witness)
    advance(coordinator, owner)
    shutil.copyfile(before_owner, owner.path)
    shutil.copyfile(before_witness, witness.path)
    # Deliberate laboratory limitation: valid HMAC over an older signed state
    # cannot attest it is the latest. Hardware monotonic anchor still required.
    assert coordinator.recover(NS)["status"] == "STABLE_LAB_ONLY"
    assert owner.snapshot(NS)["owner_epoch"] == 0


@pytest.mark.parametrize("column,value", [
    ("state_sha", "0" * 64),
    ("state_mac", "0" * 64),
    ("epoch", 123),
    ("revision", 8),
])
def test_witness_stable_record_tampering_is_detected(tmp_path, column, value):
    _, witness, _ = setup_lab(tmp_path)
    with sqlite3.connect(witness.path) as db:
        db.execute(f"UPDATE witness SET {column}=? WHERE namespace=?", (value, NS))
    with pytest.raises(WitnessBlocked, match="MAC mismatch"):
        witness.snapshot(NS)


@pytest.mark.parametrize("column,value", [
    ("pending", '{"namespace":"project-alpha"}'),
    ("pending_mac", "0" * 64),
])
def test_witness_pending_tamper_is_detected(tmp_path, column, value):
    owner, witness, _ = setup_lab(tmp_path)
    state = owner.snapshot(NS)
    witness.prepare(NS, "req1", state, acquire_proposal(state)["next_state"])
    with sqlite3.connect(witness.path) as db:
        db.execute(f"UPDATE witness SET {column}=? WHERE namespace=?", (value, NS))
    with pytest.raises(WitnessBlocked):
        witness.snapshot(NS)


def test_witness_secret_rotation_or_loss_fails_closed(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    replacement = WitnessEmulator(witness.path, test_key=b"y" * 32)
    with pytest.raises(WitnessBlocked, match="MAC mismatch"):
        replacement.snapshot(NS)


@pytest.mark.parametrize("bad_key", [None, b"short", "string", 14])
def test_reject_invalid_explicit_test_keys(tmp_path, bad_key):
    if bad_key is None:
        assert isinstance(WitnessEmulator(tmp_path / "valid.sqlite3"), WitnessEmulator)
    else:
        with pytest.raises(WitnessBlocked):
            WitnessEmulator(tmp_path / "fail.sqlite3", test_key=bad_key)


@pytest.mark.parametrize("namespace", ["../outside", "bad' or 1=1", "", "x y"])
def test_invalid_namespace_rejected(tmp_path, namespace):
    witness = WitnessEmulator(tmp_path / "w.sqlite3", test_key=KEY)
    with pytest.raises(WitnessBlocked):
        witness.initialize(namespace, genesis())


def test_duplicate_witness_bootstrap_rejected(tmp_path):
    _, witness, _ = setup_lab(tmp_path)
    with pytest.raises(WitnessBlocked, match="already initialized"):
        witness.initialize(NS, genesis())


def test_uninitialized_namespace_fail_closed(tmp_path):
    witness = WitnessEmulator(tmp_path / "w.sqlite3", test_key=KEY)
    with pytest.raises(WitnessBlocked, match="uninitialized"):
        witness.snapshot(NS)


def test_coordinator_rejects_invalid_failpoint_without_mutation(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    with pytest.raises(WitnessBlocked, match="failpoint"):
        coordinator.apply(NS, "req1", acquire_proposal(owner.snapshot(NS)), now=NOW,
                          failpoint="run_worker")
    assert owner.snapshot(NS)["store_revision"] == 0
    assert witness.snapshot(NS)["pending"] is None


def test_owner_cas_failure_keeps_witness_pending_and_blocks(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    invalid = acquire_proposal(owner.snapshot(NS))
    invalid["requires_atomic_durable_cas"] = False
    with pytest.raises(WitnessBlocked, match="invalid owner CAS"):
        coordinator.apply(NS, "req1", invalid, now=NOW)
    assert witness.snapshot(NS)["pending"] is not None
    assert coordinator.recover(NS)["status"] == "PENDING_WITH_OLD_DB_BLOCKED"


def test_two_coordinators_one_witness_prepare_wins(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    barrier = threading.Barrier(2)

    def contender(index):
        barrier.wait(timeout=5)
        try:
            coordinator.apply(NS, "req" + str(index),
                              acquire_proposal(before, owner="o" + str(index)), now=NOW)
            return "COMMITTED"
        except WitnessBlocked:
            return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(contender, (1, 2)))
    assert sorted(outcomes) == ["COMMITTED", "REJECTED"]
    assert coordinator.recover(NS)["status"] == "STABLE_LAB_ONLY"


def test_bounded_request_targets_are_checked(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    malformed = acquire_proposal(before)["next_state"]
    malformed["owner_epoch"] = -1
    with pytest.raises(WitnessBlocked):
        witness.prepare(NS, "req1", before, malformed)


def test_coordinator_refuses_naive_clock(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    with pytest.raises(WitnessBlocked, match="timezone-aware"):
        coordinator.apply(NS, "req1", acquire_proposal(owner.snapshot(NS)),
                          now=NOW.replace(tzinfo=None))


def test_optional_actual_m003_adapter_smoke(tmp_path):
    """Runs against the *real* M003 source when available in the repo/CI.

    Local standalone M004 tests do not fabricate an M003 source replica.
    """
    m003 = pytest.importorskip("openremaster.m003_cas_lab")
    own = m003.CASLab(tmp_path / "actual_m003.sqlite3")
    own.create_namespace(NS)
    witness = WitnessEmulator(tmp_path / "witness.sqlite3", test_key=KEY)
    witness.initialize(NS, own.snapshot(NS))
    coord = TwoStoreCoordinatorLab(own, witness)
    assert advance(coord, own)["status"] == "TWO_STORE_LAB_ONLY"


def test_pending_recovery_does_not_accept_unplanned_db_state(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    witness.prepare(NS, "req1", before, acquire_proposal(before)["next_state"])
    changed = acquire_proposal(before, owner="unplanned-owner")["next_state"]
    with sqlite3.connect(owner.path) as db:
        db.execute("UPDATE states SET revision=?,epoch=?,payload=? WHERE namespace=?",
                   (1, 1, canonical_json(changed), NS))
    with pytest.raises(WitnessBlocked, match="PENDING_DB_DIVERGENCE"):
        coordinator.recover(NS)


def test_stale_prepared_intent_cannot_reappear_after_finalize(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    prior = owner.snapshot(NS)
    ticket = witness.prepare(NS, "req1", prior, acquire_proposal(prior)["next_state"])
    own_proposal = acquire_proposal(prior)
    owner.apply(NS, "req1", own_proposal, (0, 0), now=NOW)
    witness.finalize(NS, ticket, owner.snapshot(NS))
    with pytest.raises(WitnessBlocked):
        witness.finalize(NS, ticket, owner.snapshot(NS))
    assert witness.snapshot(NS)["pending"] is None


def test_coordinator_rejects_owner_adapter_that_reports_authorization(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    original = owner.apply
    def unsafe(*args, **kwargs):
        result = original(*args, **kwargs)
        return {**result, "dispatch_authorized": True}
    owner.apply = unsafe
    with pytest.raises(WitnessBlocked, match="unexpectedly authorized"):
        advance(coordinator, owner)
    assert coordinator.recover(NS)["status"] == "FORWARD_COMMITTED_LAB_ONLY"
    assert coordinator.recover(NS)["status"] == "STABLE_LAB_ONLY"


def test_witness_prepare_requires_monotonic_revision(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    after = acquire_proposal(before)["next_state"]
    after["store_revision"] = 0
    with pytest.raises(WitnessBlocked, match="nonmonotonic"):
        witness.prepare(NS, "req1", before, after)
    assert witness.snapshot(NS)["pending"] is None


def test_corrupted_owner_state_blocks_initial_witness_prepare(tmp_path):
    owner, witness, coordinator = setup_lab(tmp_path)
    before = owner.snapshot(NS)
    before["schema"] = "UNKNOWN"
    with pytest.raises(WitnessBlocked, match="incompatible"):
        witness.prepare(NS, "req1", before, acquire_proposal(owner.snapshot(NS))["next_state"])
