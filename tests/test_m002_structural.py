"""Offline structural contract tests: no broker, worker, database, or secrets."""
import copy
from datetime import datetime, timedelta, timezone
import pytest
from openremaster.m002_structural import (
    Rejected, SCHEMA, ZERO_HASH, digest_json, inspect_fence,
    propose_acquire, propose_renew, propose_release,
    journal_event, project_journal, check_receipt_binding,
)

NOW = datetime(2026, 10, 13, 20, 0, tzinfo=timezone.utc)

def free():
    return dict(schema=SCHEMA + '.OwnerSnapshot', store_revision=4,
                owner_epoch=8, status='FREE', job_id=None,
                owner_id=None, attempt_id=None, expires_utc=None)

def claim():
    return dict(job_id='job-1', owner_id='owner-a', attempt_id='attempt-1', owner_epoch=9)

def active():
    return propose_acquire(free(), job_id='job-1', owner_id='owner-a',
        attempt_id='attempt-1', ttl_seconds=30, now=NOW)['next_state']

def receipt_and_job():
    job = {**claim(), 'worker_id':'worker-1','revision':'a'*40,'corpus_sha256':'b'*64}
    evidence=b'synthetic-evidence-only'
    receipt={**job,'schema':SCHEMA+'.Receipt','status':'PASS',
             'evidence_sha256':__import__('hashlib').sha256(evidence).hexdigest()}
    return job,receipt,evidence


def test_acquire_is_only_cas_proposal():
    p = propose_acquire(free(), job_id='job-1',owner_id='owner-a',attempt_id='attempt-1',ttl_seconds=30,now=NOW)
    assert p['kind']=='ACQUIRE_PROPOSAL_ONLY'
    assert p['requires_atomic_durable_cas'] is True
    assert p['expected_store_revision']==4
    assert p['next_state']['store_revision']==5
    assert p['next_state']['owner_epoch']==9


def test_fencing_matches_but_never_authorizes():
    assert inspect_fence(active(), claim(), now=NOW)=='STRUCTURAL_MATCH_NOT_AUTHORIZED'

@pytest.mark.parametrize('alter', ['job_id','owner_id','attempt_id','owner_epoch'])
def test_fence_blocks_stale_identifiers(alter):
    token=claim(); token[alter]='other' if alter!='owner_epoch' else 8
    with pytest.raises(Rejected): inspect_fence(active(), token, now=NOW)

@pytest.mark.parametrize('snapshot', ['active','expired'])
def test_cannot_steal_active_lease_or_renew_expired(snapshot):
    state=active()
    if snapshot=='active':
        with pytest.raises(Rejected): propose_acquire(state,job_id='other',owner_id='owner-b',attempt_id='a2',ttl_seconds=20,now=NOW)
    else:
        with pytest.raises(Rejected): propose_renew(state,claim(),ttl_seconds=30,now=NOW+timedelta(seconds=30))


def test_reacquire_expired_lease_increments_epoch():
    state=active()
    p=propose_acquire(state,job_id='job-2',owner_id='owner-b',attempt_id='a2',ttl_seconds=20,now=NOW+timedelta(seconds=30))
    assert p['next_state']['owner_epoch']==10
    assert p['expected_store_revision']==5


def test_renew_advances_store_revision_not_epoch():
    p=propose_renew(active(),claim(),ttl_seconds=60,now=NOW+timedelta(seconds=1))
    assert p['next_state']['owner_epoch']==9
    assert p['next_state']['store_revision']==6


def test_release_only_proposes_free_state():
    p=propose_release(active(),claim(),now=NOW)
    assert p['kind']=='RELEASE_PROPOSAL_ONLY'
    assert p['next_state']['owner_epoch']==9
    assert p['next_state']['status']=='FREE'

@pytest.mark.parametrize('bad', [True,1.1,0,61])
def test_invalid_ttl_rejected(bad):
    with pytest.raises(Rejected): propose_acquire(free(),job_id='j',owner_id='o',attempt_id='a',ttl_seconds=bad,now=NOW)


def test_unknown_snapshot_fields_are_not_silently_accepted():
    s=free();s['trusted']=True
    with pytest.raises(Rejected):propose_acquire(s,job_id='j',owner_id='o',attempt_id='a',ttl_seconds=30,now=NOW)


def test_naive_clock_refused():
    with pytest.raises(Rejected): propose_acquire(free(),job_id='j',owner_id='o',attempt_id='a',ttl_seconds=30,now=NOW.replace(tzinfo=None))


def event_chain(items):
    rows=[];prior=ZERO_HASH
    for attempt,kind in items:
        row=journal_event(len(rows),'job-1',attempt,kind,prior)
        rows.append(row);prior=row['sha256']
    return rows


def test_latest_attempt_unknown_even_if_old_completed():
    rows=event_chain([('a1','ATTEMPT_STARTED'),('a1','EXECUTION_STARTED'),('a1','EXECUTION_FINISHED'),('a1','VALIDATION_FINISHED'),('a1','ACCEPTANCE_FINISHED'),('a2','ATTEMPT_STARTED'),('a2','EXECUTION_STARTED')])
    result=project_journal('job-1',rows)
    assert result['status']=='BLOCKED_UNKNOWN_OUTCOME'
    assert result['latest_attempt_id']=='a2'
    assert result['dispatch_authorized'] is False

@pytest.mark.parametrize('sequence,expected', [
    ([], 'UNKNOWN'),
    ([('a1','ATTEMPT_STARTED')], 'NOT_STARTED'),
    ([('a1','ATTEMPT_STARTED'),('a1','EXECUTION_STARTED')], 'BLOCKED_UNKNOWN_OUTCOME'),
    ([('a1','ATTEMPT_STARTED'),('a1','EXECUTION_STARTED'),('a1','EXECUTION_FINISHED')], 'RESUME_VALIDATION_CANDIDATE_ONLY'),
    ([('a1','ATTEMPT_STARTED'),('a1','EXECUTION_STARTED'),('a1','EXECUTION_FINISHED'),('a1','VALIDATION_FINISHED')], 'RESUME_ACCEPTANCE_CANDIDATE_ONLY'),
    ([('a1','ATTEMPT_STARTED'),('a1','ATTEMPT_FAILED')], 'FAILED'),
])
def test_journal_projection(sequence,expected):
    assert project_journal('job-1',event_chain(sequence))['status']==expected

@pytest.mark.parametrize('change', ['seq','hash','prev','job','attempt','transition'])
def test_journal_rejects_missing_or_forged_order(change):
    rows=event_chain([('a1','ATTEMPT_STARTED'),('a1','EXECUTION_STARTED')])
    if change=='seq':rows[1]['seq']=0
    elif change=='hash':rows[1]['sha256']='f'*64
    elif change=='prev':rows[1]['prev_sha256']='f'*64
    elif change=='job':rows[1]['job_id']='job-2'
    elif change=='attempt':rows[1]['attempt_id']='a2'
    else:rows[1]['event']='ACCEPTANCE_FINISHED'
    with pytest.raises(Rejected):project_journal('job-1',rows)


def test_unreconciled_old_attempt_must_not_be_retried():
    rows=event_chain([('a1','ATTEMPT_STARTED'),('a1','EXECUTION_STARTED'),('a2','ATTEMPT_STARTED')])
    with pytest.raises(Rejected,match='unreconciled'):project_journal('job-1',rows)


def test_receipt_binding_only_untrusted_even_with_hash_match():
    job,receipt,evidence=receipt_and_job()
    assert check_receipt_binding(job,receipt,evidence,active(),now=NOW)=='BOUND_UNAUTHENTICATED_NOT_ACCEPTED'

@pytest.mark.parametrize('change', ['evidence','job','epoch','revision','corpus','status'])
def test_receipt_fail_closed(change):
    job,receipt,evidence=receipt_and_job()
    if change=='evidence':evidence=b'forged'
    elif change=='job':receipt['job_id']='other'
    elif change=='epoch':receipt['owner_epoch']=8
    elif change=='revision':receipt['revision']='c'*40
    elif change=='corpus':receipt['corpus_sha256']='d'*64
    else:receipt['status']='UNKNOWN'
    with pytest.raises(Rejected):check_receipt_binding(job,receipt,evidence,active(),now=NOW)


def test_receipt_expired_fence_rejected():
    job,receipt,evidence=receipt_and_job()
    with pytest.raises(Rejected):check_receipt_binding(job,receipt,evidence,active(),now=NOW+timedelta(seconds=30))


def test_canonical_digest_rejects_nonfinite():
    assert digest_json({'x':1,'y':2})==digest_json({'y':2,'x':1})
    with pytest.raises(Rejected):digest_json({'x':float('nan')})


def test_rounding_cannot_create_nonadvancing_renewal():
    s = active()
    with pytest.raises(Rejected, match='stored expiry'):
        propose_renew(s, claim(), ttl_seconds=30, now=NOW + timedelta(microseconds=999999))
