"""M002 *pure* structural proposals. Not an admission authority or executor.

No I/O, credentials, signing, durable CAS, leases, dispatch, or worker execution.
All successful responses remain unauthenticated and cannot authorize side effects.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

SCHEMA = 'ORCH-M002.Structural.v0'
SHA40 = re.compile(r'[0-9a-f]{40}\Z')
SHA64 = re.compile(r'[0-9a-f]{64}\Z')
IDENTITY = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z')
ZERO_HASH = '0' * 64


class Rejected(ValueError):
    """Incomplete, inconsistent, or unsafe structural input."""


def _keys(value, required, name):
    if type(value) is not dict or set(value) != set(required):
        raise Rejected(f'{name}: missing or unknown fields')


def _id(value, name):
    if type(value) is not str or not IDENTITY.fullmatch(value):
        raise Rejected(f'{name}: invalid identifier')


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise Rejected(f'{name}: invalid integer')


def _time(value, name):
    if type(value) is not str or not value.endswith('Z'):
        raise Rejected(f'{name}: expected RFC3339 UTC Z timestamp')
    try:
        t = datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as e:
        raise Rejected(f'{name}: invalid UTC timestamp') from e
    if t.utcoffset() != timedelta(0):
        raise Rejected(f'{name}: non-UTC timestamp')
    return t


def _now(value):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Rejected('now must be timezone-aware')
    return value.astimezone(timezone.utc)


def _timestamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def digest_json(value):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as e:
        raise Rejected('not canonicalizable JSON') from e
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def _snapshot(state):
    _keys(state, ('schema', 'store_revision', 'owner_epoch', 'status', 'job_id',
                  'owner_id', 'attempt_id', 'expires_utc'), 'owner snapshot')
    if state['schema'] != SCHEMA + '.OwnerSnapshot':
        raise Rejected('unrecognized owner snapshot version')
    _integer(state['store_revision'], 'store_revision')
    _integer(state['owner_epoch'], 'owner_epoch')
    if state['status'] == 'FREE':
        if any(state[k] is not None for k in ('job_id', 'owner_id', 'attempt_id', 'expires_utc')):
            raise Rejected('FREE snapshot has an owner')
    elif state['status'] == 'ACTIVE':
        _integer(state['owner_epoch'], 'active epoch', 1)
        for k in ('job_id', 'owner_id', 'attempt_id'):
            _id(state[k], k)
        _time(state['expires_utc'], 'expires_utc')
    else:
        raise Rejected('unknown owner state')
    return state


def _fence(state, token, now):
    _snapshot(state)
    _keys(token, ('job_id', 'owner_id', 'attempt_id', 'owner_epoch'), 'fence')
    for k in ('job_id', 'owner_id', 'attempt_id'):
        _id(token[k], k)
    _integer(token['owner_epoch'], 'owner_epoch', 1)
    if state['status'] != 'ACTIVE' or _time(state['expires_utc'], 'expires_utc') <= _now(now):
        raise Rejected('lease is inactive or expired')
    if any(state[k] != token[k] for k in token):
        raise Rejected('stale owner/attempt/epoch fence')


def inspect_fence(state, token, *, now):
    """A match is *not* authority: caller must independently check signed CAS state."""
    _fence(state, token, now)
    return 'STRUCTURAL_MATCH_NOT_AUTHORIZED'


def propose_acquire(state, *, job_id, owner_id, attempt_id, ttl_seconds, now):
    """Return versioned CAS proposal, NEVER a granted lease."""
    _snapshot(state)
    for key, val in (('job_id', job_id), ('owner_id', owner_id), ('attempt_id', attempt_id)):
        _id(val, key)
    _integer(ttl_seconds, 'ttl_seconds', 1)
    if ttl_seconds > 60:
        raise Rejected('ttl exceeds synthetic bound')
    moment = _now(now)
    if state['status'] == 'ACTIVE' and _time(state['expires_utc'], 'expires_utc') > moment:
        raise Rejected('active lease must not be displaced')
    next_state = {
        'schema': SCHEMA + '.OwnerSnapshot',
        'store_revision': state['store_revision'] + 1,
        'owner_epoch': state['owner_epoch'] + 1,
        'status': 'ACTIVE', 'job_id': job_id, 'owner_id': owner_id,
        'attempt_id': attempt_id, 'expires_utc': _timestamp(moment + timedelta(seconds=ttl_seconds)),
    }
    return {'kind': 'ACQUIRE_PROPOSAL_ONLY', 'expected_store_revision': state['store_revision'],
            'next_state': next_state, 'requires_atomic_durable_cas': True}


def propose_renew(state, token, *, ttl_seconds, now):
    _fence(state, token, now)
    _integer(ttl_seconds, 'ttl_seconds', 1)
    if ttl_seconds > 60:
        raise Rejected('ttl exceeds synthetic bound')
    new_expiry = _now(now) + timedelta(seconds=ttl_seconds)
    encoded_expiry = _timestamp(new_expiry)
    if _time(encoded_expiry, 'renewal expiry') <= _time(state['expires_utc'], 'expires_utc'):
        raise Rejected('renewal must advance stored expiry')
    next_state = dict(state, store_revision=state['store_revision'] + 1,
                      expires_utc=encoded_expiry)
    return {'kind': 'RENEW_PROPOSAL_ONLY', 'expected_store_revision': state['store_revision'],
            'next_state': next_state, 'requires_atomic_durable_cas': True}


def propose_release(state, token, *, now):
    _fence(state, token, now)
    next_state = dict(state, store_revision=state['store_revision'] + 1,
                      status='FREE', job_id=None, owner_id=None, attempt_id=None, expires_utc=None)
    return {'kind': 'RELEASE_PROPOSAL_ONLY', 'expected_store_revision': state['store_revision'],
            'next_state': next_state, 'requires_atomic_durable_cas': True}


EVENTS = ('ATTEMPT_STARTED', 'EXECUTION_STARTED', 'EXECUTION_FINISHED',
          'VALIDATION_FINISHED', 'ACCEPTANCE_FINISHED', 'ATTEMPT_FAILED')
TRANSITIONS = {
    None: {'ATTEMPT_STARTED': 'STARTED'},
    'STARTED': {'EXECUTION_STARTED': 'RUNNING', 'ATTEMPT_FAILED': 'FAILED'},
    'RUNNING': {'EXECUTION_FINISHED': 'EXECUTED', 'ATTEMPT_FAILED': 'FAILED'},
    'EXECUTED': {'VALIDATION_FINISHED': 'VALIDATED', 'ATTEMPT_FAILED': 'FAILED'},
    'VALIDATED': {'ACCEPTANCE_FINISHED': 'ACCEPTED', 'ATTEMPT_FAILED': 'FAILED'},
}


def journal_event(seq, job_id, attempt_id, kind, previous_digest):
    _integer(seq, 'seq')
    _id(job_id, 'job_id')
    _id(attempt_id, 'attempt_id')
    if kind not in EVENTS or type(previous_digest) is not str or not SHA64.fullmatch(previous_digest):
        raise Rejected('invalid event/chain')
    row = {'schema': SCHEMA + '.Event', 'seq': seq, 'job_id': job_id,
           'attempt_id': attempt_id, 'event': kind, 'prev_sha256': previous_digest}
    return {**row, 'sha256': digest_json(row)}


def project_journal(job_id, rows):
    """Project latest attempt without treating older attempts as a current PASS.

    The hash chain only detects accidental tampering, NOT author authenticity.
    """
    _id(job_id, 'job_id')
    if type(rows) is not list:
        raise Rejected('journal must be a list')
    expected_digest = ZERO_HASH
    state = None
    attempt = None
    prior_attempts = set()
    for index, row in enumerate(rows):
        _keys(row, ('schema', 'seq', 'job_id', 'attempt_id', 'event', 'prev_sha256', 'sha256'), 'event')
        if row['schema'] != SCHEMA + '.Event' or row['job_id'] != job_id:
            raise Rejected('foreign event/unsupported version')
        if type(row['seq']) is not int or row['seq'] != index:
            raise Rejected('missing, duplicate, or reordered event sequence')
        if row['prev_sha256'] != expected_digest:
            raise Rejected('journal chain broken')
        content = {k: v for k, v in row.items() if k != 'sha256'}
        if row['sha256'] != digest_json(content):
            raise Rejected('journal event hash mismatch')
        _id(row['attempt_id'], 'attempt_id')
        event = row['event']
        if event not in EVENTS:
            raise Rejected('unknown event')
        if row['attempt_id'] != attempt:
            if event != 'ATTEMPT_STARTED' or row['attempt_id'] in prior_attempts:
                raise Rejected('invalid new attempt/reopened attempt')
            if state not in (None, 'FAILED', 'ACCEPTED'):
                raise Rejected('unreconciled previous attempt')
            prior_attempts.add(row['attempt_id'])
            attempt = row['attempt_id']
            state = None
        state = TRANSITIONS.get(state, {}).get(event)
        if state is None:
            raise Rejected('invalid per-attempt transition')
        expected_digest = row['sha256']
    outcomes = {None: 'UNKNOWN', 'STARTED': 'NOT_STARTED',
                'RUNNING': 'BLOCKED_UNKNOWN_OUTCOME',
                'EXECUTED': 'RESUME_VALIDATION_CANDIDATE_ONLY',
                'VALIDATED': 'RESUME_ACCEPTANCE_CANDIDATE_ONLY',
                'ACCEPTED': 'COMPLETED_UNAUTHENTICATED', 'FAILED': 'FAILED'}
    return {'status': outcomes[state], 'latest_attempt_id': attempt,
            'events': len(rows), 'last_digest': expected_digest,
            'dispatch_authorized': False}


def check_receipt_binding(job, receipt, evidence_bytes, owner_state, *, now):
    """Digest+identity matching is NOT signature, semantic evidence, or authority."""
    fields = ('job_id', 'attempt_id', 'worker_id', 'owner_id', 'owner_epoch',
              'revision', 'corpus_sha256')
    _keys(job, fields, 'job')
    _keys(receipt, fields + ('schema', 'status', 'evidence_sha256'), 'receipt')
    if receipt['schema'] != SCHEMA + '.Receipt' or receipt['status'] != 'PASS':
        raise Rejected('unsupported receipt or non-PASS claim')
    for key in ('job_id', 'attempt_id', 'worker_id', 'owner_id'):
        _id(job[key], key)
    _integer(job['owner_epoch'], 'owner_epoch', 1)
    if type(job['revision']) is not str or not SHA40.fullmatch(job['revision']):
        raise Rejected('invalid source commit')
    if type(job['corpus_sha256']) is not str or not SHA64.fullmatch(job['corpus_sha256']):
        raise Rejected('invalid source corpus identity')
    if any(job[key] != receipt[key] for key in fields):
        raise Rejected('job/receipt identity mismatch')
    _fence(owner_state, {key: job[key] for key in ('job_id', 'attempt_id', 'owner_id', 'owner_epoch')}, now)
    if type(evidence_bytes) is not bytes or not evidence_bytes:
        raise Rejected('missing evidence bytes')
    expected = hashlib.sha256(evidence_bytes).hexdigest()
    if receipt['evidence_sha256'] != expected:
        raise Rejected('evidence digest mismatch')
    return 'BOUND_UNAUTHENTICATED_NOT_ACCEPTED'
