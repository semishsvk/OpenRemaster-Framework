import pytest
from openremaster.m010_durable_recovery import DurableReviewLedger, RecoveryHold
A='a'*64;B='b'*64;C='c'*64

def init(tmp_path):
    l=DurableReviewLedger(tmp_path);l.initialize('project-one',1,1,1,A);return l

def prepare(l,op='operation-001',challenge='challenge-001',candidate=B):
    return l.prepare(op=op,scope='project-one',challenge=challenge,prior_digest=A,candidate_digest=candidate,sequence=2,epoch=2,fence=2)

def test_initial_state_non_authorizing(tmp_path):
    with init(tmp_path) as l:
        assert l.status('project-one')['native_worker_dispatch_authorized'] is False

def test_prepared_survives_restart_and_blocks_duplicate(tmp_path):
    with init(tmp_path) as l: prepare(l)
    with DurableReviewLedger(tmp_path) as l:
        assert l.status('project-one')['operations'][0][1]=='PREPARED'
        with pytest.raises(RecoveryHold): prepare(l,'operation-002','challenge-002')

def test_unknown_survives_restart_and_never_autocommits(tmp_path):
    with init(tmp_path) as l: prepare(l);l.mark_unknown('operation-001')
    with DurableReviewLedger(tmp_path) as l:
        assert l.status('project-one')['head'][3]==A
        assert l.status('project-one')['operations'][0][1]=='UNKNOWN'
        with pytest.raises(RecoveryHold): prepare(l,'operation-002','challenge-002')

def test_explicit_confirm_is_review_only(tmp_path):
    with init(tmp_path) as l: prepare(l);l.mark_unknown('operation-001');l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C)
    with DurableReviewLedger(tmp_path) as l:
        s=l.status('project-one');assert s['head']==(2,2,2,B);assert s['operations'][0][1]=='COMMIT_RECORDED_REVIEW_ONLY';assert not s['external_current_head_verified']

def test_rejection_does_not_move_head(tmp_path):
    with init(tmp_path) as l: prepare(l);l.reconcile('operation-001',outcome='REJECTED');assert l.status('project-one')['head'][3]==A

def test_double_confirm_rejected(tmp_path):
    with init(tmp_path) as l:
        prepare(l);l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C)
        with pytest.raises(RecoveryHold): l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C)

def test_head_rollback_refused(tmp_path):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold): l.initialize('project-one',0,1,1,A)

def test_existing_head_reopen_idempotent(tmp_path):
    with init(tmp_path) as l: l.initialize('project-one',1,1,1,A)

def test_replay_challenge_blocked_after_reject(tmp_path):
    with init(tmp_path) as l:
        prepare(l);l.reconcile('operation-001',outcome='REJECTED')
        with pytest.raises(RecoveryHold):prepare(l,'operation-002','challenge-001')

def test_partition_unknown_requires_reconciliation(tmp_path):
    with init(tmp_path) as l:
        prepare(l);l.reconcile('operation-001',outcome='UNKNOWN')
        assert l.status('project-one')['head'][3]==A

def test_unconfirmed_receipt_refused(tmp_path):
    with init(tmp_path) as l:
        prepare(l)
        with pytest.raises(RecoveryHold):l.reconcile('operation-001',outcome='UNKNOWN',receipt_digest=C)

@pytest.mark.parametrize('seq,epoch,fence,prior',[ (2,0,2,A),(2,3,2,A),(3,2,2,A),(2,2,1,A),(2,2,2,C),(True,2,2,A)])
def test_invalid_monotonic_candidate(tmp_path,seq,epoch,fence,prior):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold):l.prepare(op='operation-001',scope='project-one',challenge='challenge-001',prior_digest=prior,candidate_digest=B,sequence=seq,epoch=epoch,fence=fence)

@pytest.mark.parametrize('value',['oops',None,False,1,'g'*64])
def test_invalid_digest(tmp_path,value):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold):l.prepare(op='operation-001',scope='project-one',challenge='challenge-001',prior_digest=value,candidate_digest=B,sequence=2,epoch=2,fence=2)

def test_unknown_op_fails(tmp_path):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold):l.mark_unknown('missing-op')

def test_corrupt_schema_fails_closed(tmp_path):
    with init(tmp_path) as l:l.db.execute("UPDATE meta SET v='tampered' WHERE k='schema'")
    with pytest.raises(RecoveryHold):DurableReviewLedger(tmp_path)

def test_unexpected_confirmation_without_prepare(tmp_path):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold):l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C)

def _create_symlink_or_skip(link,target):
    """Only Windows missing-privilege setup is an environment limitation."""
    try:
        link.symlink_to(target)
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows identity lacks symlink privilege; real symlink rejection remains unverified here')
        raise
def test_symlinked_ledger_refused(tmp_path):
    """Real filesystem security test; never replaced with simulated evidence."""
    other=tmp_path/'outside.sqlite3';other.write_bytes(b'untrusted')
    _create_symlink_or_skip(tmp_path/'m010-review-only.sqlite3',other)
    with pytest.raises(RecoveryHold,match='refusing symlinked ledger'):
        DurableReviewLedger(tmp_path)
    assert other.read_bytes()==b'untrusted'

def test_same_scope_competing_candidate_fails(tmp_path):
    with init(tmp_path) as l:
        prepare(l)
        with pytest.raises(RecoveryHold):prepare(l,'operation-002','challenge-002',C)

def test_symlink_guard_refuses_before_database_connect_simulated(tmp_path,monkeypatch):
    """Branch-only evidence; real filesystem symlink test remains separate."""
    from pathlib import Path
    import openremaster.m010_durable_recovery as recovery
    ledger=tmp_path/'m010-review-only.sqlite3'
    original=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda path:True if path==ledger else original(path))
    def forbidden_connect(*args,**kwargs):
        pytest.fail('Symlink guard must reject before SQLite opens the ledger')
    monkeypatch.setattr(recovery.sqlite3,'connect',forbidden_connect)
    with pytest.raises(RecoveryHold,match='refusing symlinked ledger'):
        DurableReviewLedger(tmp_path)
    assert not ledger.exists()

def test_missing_symlink_privilege_is_explicit_environment_skip(tmp_path,monkeypatch):
    from pathlib import Path
    error=OSError('synthetic missing privilege');error.winerror=1314
    def unavailable(*args,**kwargs):raise error
    monkeypatch.setattr(Path,'symlink_to',unavailable)
    with pytest.raises(pytest.skip.Exception,match='real symlink rejection remains unverified'):
        _create_symlink_or_skip(tmp_path/'link',tmp_path/'target')

@pytest.mark.parametrize('winerror',[5,None])
def test_unexpected_symlink_setup_errors_are_not_skipped(tmp_path,monkeypatch,winerror):
    from pathlib import Path
    error=OSError('synthetic unexpected setup failure')
    if winerror is not None:error.winerror=winerror
    def broken(*args,**kwargs):raise error
    monkeypatch.setattr(Path,'symlink_to',broken)
    with pytest.raises(OSError,match='unexpected setup failure'):
        _create_symlink_or_skip(tmp_path/'link',tmp_path/'target')

def test_missing_receipt_confirmation_fails(tmp_path):
    with init(tmp_path) as l:
        prepare(l)
        with pytest.raises(RecoveryHold):l.reconcile('operation-001',outcome='COMMIT_CONFIRMED')
        assert l.status('project-one')['head'][3]==A

def test_different_scope_cannot_reuse_challenge(tmp_path):
    with init(tmp_path) as l:
        l.initialize('project-two',1,1,1,A)
        prepare(l)
        with pytest.raises(RecoveryHold):l.prepare(op='operation-002',scope='project-two',challenge='challenge-001',prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2)

def test_no_implicit_second_job_even_after_confirm(tmp_path):
    with init(tmp_path) as l:
        prepare(l)
        l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C)
        with pytest.raises(RecoveryHold):l.prepare(op='operation-002',scope='project-one',challenge='challenge-002',prior_digest=B,candidate_digest=C,sequence=3,epoch=3,fence=3)

# Additional bounded crash and rollback negative fixtures. Child Python processes
# operate only on pytest-owned local SQLite files, never a native worker.
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def test_failpoint_before_prepare_commit_rolls_back(tmp_path):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold, match='BEFORE_PREPARE_COMMIT'):
            l.prepare(op='operation-001',scope='project-one',challenge='challenge-001',
                prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2,
                failpoint='BEFORE_PREPARE_COMMIT')
        assert l.status('project-one')['operations']==[]


def test_failpoint_after_prepare_commit_retains_prepared(tmp_path):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold, match='AFTER_PREPARE_COMMIT'):
            l.prepare(op='operation-001',scope='project-one',challenge='challenge-001',
                prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2,
                failpoint='AFTER_PREPARE_COMMIT')
    with DurableReviewLedger(tmp_path) as l:
        assert l.status('project-one')['operations']==[('operation-001','PREPARED')]
        assert l.status('project-one')['head'][3]==A


def test_failpoint_after_local_head_update_is_atomic(tmp_path):
    with init(tmp_path) as l:
        prepare(l)
        with pytest.raises(RecoveryHold, match='AFTER_HEAD_UPDATE_BEFORE_COMMIT'):
            l.reconcile('operation-001', outcome='COMMIT_CONFIRMED',
                        receipt_digest=C, failpoint='AFTER_HEAD_UPDATE_BEFORE_COMMIT')
    with DurableReviewLedger(tmp_path) as l:
        status=l.status('project-one')
        assert status['head']==(1,1,1,A)
        assert status['operations']==[('operation-001','PREPARED')]


def test_failpoint_after_reconcile_commit_persists(tmp_path):
    with init(tmp_path) as l:
        prepare(l)
        with pytest.raises(RecoveryHold, match='AFTER_RECONCILE_COMMIT'):
            l.reconcile('operation-001', outcome='COMMIT_CONFIRMED',
                        receipt_digest=C, failpoint='AFTER_RECONCILE_COMMIT')
    with DurableReviewLedger(tmp_path) as l:
        status=l.status('project-one')
        assert status['head']==(2,2,2,B)
        assert status['operations']==[('operation-001','COMMIT_RECORDED_REVIEW_ONLY')]
        assert status['native_worker_dispatch_authorized'] is False


@pytest.mark.parametrize('failpoint,phase,expected,head',[
 ('BEFORE_PREPARE_COMMIT','prepare',71,A),
 ('AFTER_PREPARE_COMMIT','prepare',72,A),
 ('AFTER_HEAD_UPDATE_BEFORE_COMMIT','reconcile',73,A),
 ('AFTER_RECONCILE_COMMIT','reconcile',74,B),
])
def test_true_child_process_exit_crash_recovery(tmp_path,failpoint,phase,expected,head):
    with init(tmp_path) as l:
        if phase=='reconcile':prepare(l)
    # Private test-only process injects hard os._exit into the isolated ledger.
    script=r'''
import os,sys
import openremaster.m010_durable_recovery as module
from openremaster.m010_durable_recovery import DurableReviewLedger
D=sys.argv[1]; PHASE=sys.argv[2]; FAIL=sys.argv[3]; CODE=int(sys.argv[4]); A='a'*64;B='b'*64;C='c'*64
module._failure=lambda selected, at: os._exit(CODE) if selected==at else None
with DurableReviewLedger(D) as ledger:
    if PHASE=='prepare':
        ledger.prepare(op='operation-001',scope='project-one',challenge='challenge-001',prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2,failpoint=FAIL)
    else:
        ledger.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C,failpoint=FAIL)
sys.exit(99)
'''
    env=dict(os.environ)
    src=Path(__file__).resolve().parents[1]/'src'
    env['PYTHONPATH']=str(src)
    env['PYTHONDONTWRITEBYTECODE']='1'
    proc=subprocess.run([sys.executable,'-B','-c',script,str(tmp_path),phase,failpoint,str(expected)],
                        env=env,capture_output=True,text=True,timeout=15)
    assert proc.returncode==expected,(proc.returncode,proc.stdout,proc.stderr)
    with DurableReviewLedger(tmp_path) as l:
        st=l.status('project-one')
        assert st['head'][3]==head
        expected_state = (
            'COMMIT_RECORDED_REVIEW_ONLY' if failpoint == 'AFTER_RECONCILE_COMMIT'
            else 'PREPARED' if phase == 'reconcile' or failpoint == 'AFTER_PREPARE_COMMIT'
            else None
        )
        assert st['operations'] == ([] if expected_state is None else [('operation-001', expected_state)])
        assert l.db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
        assert st['native_worker_dispatch_authorized'] is False


def test_local_database_rollback_limitation_explicit(tmp_path):
    with init(tmp_path) as l:pass
    database=tmp_path/'m010-review-only.sqlite3'
    prior_bytes=database.read_bytes()
    with DurableReviewLedger(tmp_path) as l:
        prepare(l)
        l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C)
    assert database.read_bytes()!=prior_bytes
    # Simulate privileged restoration of the full old SQLite file. This *must*
    # not be represented as an external rollback-resistant authority.
    database.write_bytes(prior_bytes)
    with DurableReviewLedger(tmp_path) as l:
        assert l.status('project-one')['head'][3]==A
        assert l.status('project-one')['external_current_head_verified'] is False
        assert l.status('project-one')['native_worker_dispatch_authorized'] is False


def test_two_connections_compete_one_local_prepare_wins(tmp_path):
    with init(tmp_path):pass
    def contest(label):
        try:
            with DurableReviewLedger(tmp_path) as l:
                l.prepare(op='operation-'+label,scope='project-one',
                          challenge='challenge-'+label,prior_digest=A,
                          candidate_digest=B,sequence=2,epoch=2,fence=2)
                return 'WIN'
        except RecoveryHold:return 'HOLD'
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(contest,['00000001','00000002']))
    assert sorted(outcomes)==['HOLD','WIN']


def test_local_invalid_failure_points_do_not_mutate(tmp_path):
    with init(tmp_path) as l:
        with pytest.raises(RecoveryHold,match='invalid test-only'):
            l.prepare(op='operation-001',scope='project-one',challenge='challenge-001',
                      prior_digest=A,candidate_digest=B,sequence=2,epoch=2,fence=2,
                      failpoint='AFTER_NATIVE_EXECUTE')
        prepare(l)
        with pytest.raises(RecoveryHold,match='invalid test-only'):
            l.reconcile('operation-001',outcome='COMMIT_CONFIRMED',receipt_digest=C,
                        failpoint='AFTER_NATIVE_EXECUTE')
        assert l.status('project-one')['head']==(1,1,1,A)
        assert l.status('project-one')['operations']==[('operation-001','PREPARED')]
