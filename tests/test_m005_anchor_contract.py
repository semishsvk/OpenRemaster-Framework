"""M005 isolated detached signature + monotonic-hint tests, no remote service."""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import secrets
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from openremaster.m005_anchor_contract import (
    ANCHOR_SCHEMA, CHECKPOINT_SCHEMA, OWNER_SCHEMA, AnchorRejected,
    canonical_json, sha256_json, signing_message, verify_detached_anchor,
    classify_partition,
)

NOW = datetime(2026, 10, 13, 20, 0, 15, tzinfo=timezone.utc)
REVISION = 'a' * 40
CORPUS = 'b' * 64
REQUEST = 'c' * 64
AUTHORITY = 'test-authority'
WORKER = 'synthetic-worker'
NAMESPACE = 'project-alpha'


def utc(t):
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def case():
    signing_key = Ed25519PrivateKey.generate()  # ephemeral test-only; never committed
    public_key = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    checkpoint = {
        'schema': CHECKPOINT_SCHEMA, 'authority_id': AUTHORITY,
        'namespace': NAMESPACE, 'sequence': 4,
        'store_revision': 4, 'owner_epoch': 3, 'last_anchor_sha256': 'd' * 64,
    }
    owner = {
        'schema': OWNER_SCHEMA, 'status': 'ACTIVE',
        'store_revision': 5, 'owner_epoch': 4,
        'job_id': 'job-1', 'attempt_id': 'attempt-1', 'owner_id': 'owner-1',
        'expires_utc': utc(NOW + timedelta(seconds=35)),
    }
    receipt = {
        'status': 'CAS_COMMITTED_LAB_ONLY', 'store_revision': 5, 'owner_epoch': 4,
        'requires_external_witness_update': True, 'dispatch_authorized': False,
        'request_digest': REQUEST,
    }
    nonce = secrets.token_urlsafe(32)
    anchor = {
        'schema': ANCHOR_SCHEMA, 'authority_id': AUTHORITY, 'key_id': 'key-test-1',
        'namespace': NAMESPACE, 'challenge': nonce,
        'previous_anchor_sha256': checkpoint['last_anchor_sha256'],
        'sequence': 5, 'store_revision': 5, 'owner_epoch': 4,
        'source_revision': REVISION, 'corpus_sha256': CORPUS,
        'job_id': owner['job_id'], 'attempt_id': owner['attempt_id'],
        'owner_id': owner['owner_id'], 'worker_id': WORKER,
        'request_sha256': REQUEST, 'owner_snapshot_sha256': sha256_json(owner),
        'owner_receipt_sha256': sha256_json(receipt),
        'issued_utc': utc(NOW - timedelta(seconds=2)),
        'expires_utc': utc(NOW + timedelta(seconds=25)),
        'phase': 'COMMITTED', 'signature_b64': '',
    }
    params = {
        'anchor': anchor,
        'independent_checkpoint': checkpoint,
        'owner_snapshot': owner,
        'owner_receipt': receipt,
        'trusted_public_keys': {(AUTHORITY, 'key-test-1'): public_key},
        'expected_namespace': NAMESPACE,
        'expected_authority': AUTHORITY,
        'expected_worker': WORKER,
        'expected_challenge': nonce,
        'expected_source_revision': REVISION,
        'expected_corpus_sha256': CORPUS,
        'expected_request_sha256': REQUEST,
        'now': NOW,
    }
    resign(signing_key, anchor)
    return signing_key, params


def resign(private, anchor):
    anchor['signature_b64'] = base64.b64encode(private.sign(signing_message(anchor))).decode('ascii')


def verify(params):
    return verify_detached_anchor(**params)


def test_genuine_detached_signature_matches_but_never_authorizes():
    private, v = case()
    result = verify(v)
    assert result['status'] == 'SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF'
    assert result['dispatch_authorized'] is False
    assert result['worker_execution_authorized'] is False
    assert result['current_external_high_water_verified'] is False
    assert result['independent_owner_cas_authenticity_verified'] is False
    proposal = result['next_checkpoint_proposal_only']
    assert (proposal['sequence'], proposal['store_revision'], proposal['owner_epoch']) == (5, 5, 4)
    assert proposal['last_anchor_sha256'] == sha256_json(v['anchor'])


def test_ed25519_domain_separation_is_explicit():
    key, v = case()
    expected = signing_message(v['anchor'])
    assert expected.startswith(b'OpenRemaster-ORCH-M005-anchor-v0\x00')
    assert b'signature_b64' not in expected
    assert b'COMMITTED' in expected
    assert canonical_json({'text': 'štít', 'num': 42}) == canonical_json({'num': 42, 'text': 'štít'})


@pytest.mark.parametrize('field,new', [
    ('authority_id', 'impostor'), ('key_id', 'unknown-key'),
    ('namespace', 'other-space'), ('challenge', 'w' * 43),
    ('previous_anchor_sha256', 'e' * 64), ('sequence', 6),
    ('store_revision', 6), ('owner_epoch', 5),
    ('source_revision', 'f' * 40), ('corpus_sha256', 'f' * 64),
    ('job_id', 'job-2'), ('attempt_id', 'attempt-2'), ('owner_id', 'owner-2'),
    ('worker_id', 'rogue-worker'), ('request_sha256', 'f' * 64),
    ('owner_snapshot_sha256', 'f' * 64), ('owner_receipt_sha256', 'f' * 64),
    ('issued_utc', '2026-10-13T19:59:59Z'),
    ('expires_utc', '2026-10-13T20:00:00Z'), ('phase', 'PREPARED'),
    ('schema', 'ORCH-M005.Future.v1'),
])
def test_mutation_after_signature_rejected(field, new):
    key, v = case()
    v['anchor'][field] = new
    with pytest.raises(AnchorRejected): verify(v)


@pytest.mark.parametrize('change', ['worker', 'challenge', 'source', 'corpus', 'request', 'namespace', 'authority'])
def test_independent_expectations_cannot_be_changed(change):
    _, v = case()
    field = {
        'worker': 'expected_worker', 'challenge': 'expected_challenge',
        'source': 'expected_source_revision', 'corpus': 'expected_corpus_sha256',
        'request': 'expected_request_sha256', 'namespace': 'expected_namespace',
        'authority': 'expected_authority',
    }[change]
    v[field] = ('f' * (40 if change == 'source' else 64)) if change in ('source','corpus','request') else ('bogus'+('x'*32 if change=='challenge' else ''))
    with pytest.raises(AnchorRejected): verify(v)


@pytest.mark.parametrize('fault', [
    'missing', 'wrong-key', 'wrong-key-id', 'short-key',
    'invalid-base64', 'wrong-signature', 'noncanonical-padding',
])
def test_signature_trust_fail_closed(fault):
    sk, v = case()
    if fault == 'missing': v['trusted_public_keys'] = {}
    elif fault == 'wrong-key':
        alt = Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        v['trusted_public_keys'][(AUTHORITY,'key-test-1')] = alt
    elif fault == 'wrong-key-id': v['anchor']['key_id']='unauthorized-id'
    elif fault == 'short-key': v['trusted_public_keys'][(AUTHORITY,'key-test-1')]=b'not-ed25519'
    elif fault == 'invalid-base64': v['anchor']['signature_b64']='not!base64'
    elif fault == 'wrong-signature':
        v['anchor']['signature_b64']=base64.b64encode(Ed25519PrivateKey.generate().sign(signing_message(v['anchor']))).decode()
    elif fault == 'noncanonical-padding': v['anchor']['signature_b64']+='=='
    with pytest.raises(AnchorRejected): verify(v)


@pytest.mark.parametrize('fault', [
    'checkpoint-sequence', 'checkpoint-head', 'checkpoint-revision', 'checkpoint-epoch',
    'checkpoint-authority', 'checkpoint-namespace', 'checkpoint-boolean',
    'snapshot-epoch', 'snapshot-revision', 'snapshot-owner',
    'receipt-digest', 'receipt-status', 'receipt-allow-dispatch', 'receipt-owner-epoch',
])
def test_external_highwater_and_owner_consistency(fault):
    sk,v=case()
    cp=v['independent_checkpoint']; owner=v['owner_snapshot']; receipt=v['owner_receipt']
    if fault=='checkpoint-sequence': cp['sequence']=5
    elif fault=='checkpoint-head': cp['last_anchor_sha256']='f'*64
    elif fault=='checkpoint-revision': cp['store_revision']=5
    elif fault=='checkpoint-epoch': cp['owner_epoch']=5
    elif fault=='checkpoint-authority': cp['authority_id']='different'
    elif fault=='checkpoint-namespace': cp['namespace']='different'
    elif fault=='checkpoint-boolean': cp['sequence']=True
    elif fault=='snapshot-epoch': owner['owner_epoch']=3
    elif fault=='snapshot-revision': owner['store_revision']=6
    elif fault=='snapshot-owner': owner['owner_id']='rogue'
    elif fault=='receipt-digest': receipt['request_digest']='e'*64
    elif fault=='receipt-status': receipt['status']='PASS'
    elif fault=='receipt-allow-dispatch': receipt['dispatch_authorized']=True
    elif fault=='receipt-owner-epoch': receipt['owner_epoch']=3
    with pytest.raises(AnchorRejected): verify(v)


@pytest.mark.parametrize('fault', ['future', 'expired', 'long-lived', 'date-invalid', 'not-z', 'owner-expired', 'naive-clock'])
def test_time_and_expiry_fail_closed(fault):
    sk,v=case()
    if fault=='future': v['now']=NOW-timedelta(seconds=3)
    elif fault=='expired': v['now']=NOW+timedelta(seconds=26)
    elif fault=='long-lived':
        v['anchor']['expires_utc']=utc(NOW+timedelta(seconds=100));resign(sk,v['anchor'])
    elif fault=='date-invalid':
        v['anchor']['issued_utc']='2026-18-90T20:00:00Z';resign(sk,v['anchor'])
    elif fault=='not-z':
        v['anchor']['expires_utc']='2026-10-13T20:00:35+00:00';resign(sk,v['anchor'])
    elif fault=='owner-expired':
        v['owner_snapshot']['expires_utc']=utc(NOW-timedelta(seconds=1))
    elif fault=='naive-clock': v['now']=NOW.replace(tzinfo=None)
    with pytest.raises(AnchorRejected): verify(v)


def test_schema_rejects_extra_or_missing_fields_even_when_signed():
    sk,v=case()
    v['anchor']['send_command']='shell.exec'
    with pytest.raises(AnchorRejected): verify(v)
    sk,v=case()
    del v['anchor']['worker_id']
    with pytest.raises(AnchorRejected): verify(v)


def test_partitions_and_no_signed_response_never_authorize():
    for observation in ('ONLINE', 'TIMEOUT', 'PARTITIONED', 'UNKNOWN', 'STALE'):
        result = classify_partition(observation)
        assert result['dispatch_authorized'] is False
        assert result['worker_execution_authorized'] is False
        if observation != 'ONLINE': assert result['status'] == 'BLOCKED_NO_FRESH_WITNESS'
    _,v=case()
    v['anchor']=None
    with pytest.raises(AnchorRejected, match='partition'): verify(v)


def test_missing_external_highwater_fails_closed():
    _,v=case();v['independent_checkpoint']=None
    with pytest.raises(AnchorRejected, match='partition'): verify(v)


def test_stale_signed_checkpoint_and_challenge_can_be_replayed_if_both_rolled_back():
    """Known gap: a local verifier cannot establish external freshness alone."""
    _,v=case()
    once=verify(v)
    again=verify(v)  # replay of the SAME signed checkpoint + challenge + clock
    assert once == again
    assert again['dispatch_authorized'] is False
    assert again['current_external_high_water_verified'] is False


def test_old_signature_fails_against_newer_external_highwater():
    _,v=case()
    future=verify(v)['next_checkpoint_proposal_only']
    v['independent_checkpoint']=future
    with pytest.raises(AnchorRejected, match='nonmonotonic'): verify(v)


def test_signature_issuer_cannot_be_substituted_via_untrusted_key_registry():
    sk,v=case()
    v['trusted_public_keys']={('other-authority','key-test-1'): next(iter(v['trusted_public_keys'].values()))}
    with pytest.raises(AnchorRejected):verify(v)


@pytest.mark.parametrize('bad', [True,0,1.5,2**64])
def test_strict_counter_types(bad):
    _,v=case()
    v['independent_checkpoint']['store_revision']=bad
    with pytest.raises(AnchorRejected): verify(v)


def test_malformed_json_digest_is_rejected():
    with pytest.raises(AnchorRejected):sha256_json({'nan':float('nan')})
    with pytest.raises(AnchorRejected):sha256_json({'not_json':object()})


def test_second_anchor_chain_advance_is_proposal_not_finalization():
    sk,v=case()
    first=verify(v)['next_checkpoint_proposal_only']
    v['independent_checkpoint']=first
    v['owner_snapshot']['store_revision']=6
    v['owner_receipt']['store_revision']=6
    v['anchor']['sequence']=6
    v['anchor']['store_revision']=6
    v['anchor']['previous_anchor_sha256']=first['last_anchor_sha256']
    v['anchor']['owner_snapshot_sha256']=sha256_json(v['owner_snapshot'])
    v['anchor']['owner_receipt_sha256']=sha256_json(v['owner_receipt'])
    v['anchor']['challenge']=secrets.token_urlsafe(32)
    v['expected_challenge']=v['anchor']['challenge']
    resign(sk,v['anchor'])
    result=verify(v)
    assert result['next_checkpoint_proposal_only']['sequence']==6
    assert result['dispatch_authorized'] is False


def test_caller_forged_source_receipt_cannot_be_proven_independently():
    """Known gap: signer + local data can collude; this cannot authenticate M003 CAS."""
    sk,v=case()
    v['owner_receipt']['request_digest']='f'*64
    v['expected_request_sha256']='f'*64
    v['anchor']['request_sha256']='f'*64
    v['anchor']['owner_receipt_sha256']=sha256_json(v['owner_receipt'])
    resign(sk,v['anchor'])
    result=verify(v)
    assert result['independent_owner_cas_authenticity_verified'] is False
    assert result['dispatch_authorized'] is False


def test_actual_m004_emulator_composition_is_still_not_remote_authority(tmp_path):
    """Uses the unmodified M004 Git blob, not a stand-in for its state API.

    No real M003 CAS or remote authority is involved: this composes two pure lab
    boundaries and deliberately cannot upgrade the authority level.
    """
    from openremaster.m004_witness_lab import WitnessEmulator

    witness = WitnessEmulator(tmp_path / 'witness.sqlite3', test_key=b'M004 lab-only test key material!' + b'x'*8)
    genesis = {
        'schema': OWNER_SCHEMA, 'status': 'FREE', 'store_revision': 0,
        'owner_epoch': 0, 'job_id': None, 'attempt_id': None, 'owner_id': None,
        'expires_utc': None,
    }
    before = witness.initialize(NAMESPACE, genesis)
    assert before['dispatch_authorized'] is False
    signed_key, v = case()
    owner = deepcopy(v['owner_snapshot'])
    owner['store_revision'] = 1
    owner['owner_epoch'] = 1
    ticket = witness.prepare(NAMESPACE, 'synthetic-request', genesis, owner)
    assert witness.reconcile(NAMESPACE, genesis)['status'] == 'PENDING_WITH_OLD_DB_BLOCKED'
    finalized = witness.finalize(NAMESPACE, ticket, owner)
    assert finalized['dispatch_authorized'] is False
    assert witness.reconcile(NAMESPACE, owner)['status'] == 'STABLE_LAB_ONLY'
    assert witness.snapshot(NAMESPACE)['revision'] == 1
    v['owner_snapshot'] = owner
    v['owner_receipt']['store_revision'] = 1
    v['owner_receipt']['owner_epoch'] = 1
    v['independent_checkpoint']['sequence'] = 0
    v['independent_checkpoint']['store_revision'] = 0
    v['independent_checkpoint']['owner_epoch'] = 0
    v['independent_checkpoint']['last_anchor_sha256'] = '0'*64
    v['anchor']['previous_anchor_sha256'] = '0'*64
    v['anchor']['sequence'] = 1
    v['anchor']['store_revision'] = 1
    v['anchor']['owner_epoch'] = 1
    v['anchor']['owner_snapshot_sha256'] = sha256_json(owner)
    v['anchor']['owner_receipt_sha256'] = sha256_json(v['owner_receipt'])
    resign(signed_key, v['anchor'])
    result = verify(v)
    assert result['status'] == 'SIGNED_CONSISTENT_NOT_FRESHNESS_PROOF'
    assert result['dispatch_authorized'] is False
    assert result['independent_owner_cas_authenticity_verified'] is False
