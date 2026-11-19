"""Real Ed25519 laboratory signatures; no production keys or live authority."""
from dataclasses import replace
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from openremaster.m005_anchor_contract import sha256_json
from openremaster.m012_independent_head_witness import WitnessHold,WitnessTrust,verify_independent_witness
from test_m011_signed_recovery import sign as sign_receipt
from test_m012_independent_head_witness import fixture,resign,KEY,WITNESS

def raw_public(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)

@pytest.mark.parametrize('result',['COMMITTED','REJECTED'])
def test_same_signing_key_cannot_become_independent_by_renaming_authority(result):
    witness_private,args=fixture(result)
    receipt=args['receipt'];public=raw_public(witness_private)
    args['receipt_trust']=replace(args['receipt_trust'],public_keys={receipt['key_id']:public})
    sign_receipt(witness_private,receipt)
    args['witness']['m011_receipt_sha256']=sha256_json(receipt)
    resign(witness_private,args['witness'])
    # Both signatures are cryptographically valid, but the key roles are identical.
    with pytest.raises(WitnessHold,match='shared signing key material'):
        verify_independent_witness(**args)

@pytest.mark.parametrize('side',['witness_alias','receipt_alias','both_revoked_aliases'])
def test_overlapping_pinned_key_domains_are_rejected_even_with_distinct_active_signers(side):
    _,args=fixture();receipt_trust=args['receipt_trust'];witness_trust=args['witness_trust']
    receipt_keys=dict(receipt_trust.public_keys);witness_keys=dict(witness_trust.keys)
    receipt_revoked=receipt_trust.revoked_key_ids;witness_revoked=witness_trust.revoked
    if side=='witness_alias':witness_keys['receipt-key-alias']=next(iter(receipt_keys.values()))
    elif side=='receipt_alias':receipt_keys['witness-key-alias']=next(iter(witness_keys.values()))
    else:
        shared=raw_public(Ed25519PrivateKey.generate())
        receipt_keys['retired-role-key']=shared;witness_keys['retired-role-key']=shared
        receipt_revoked=receipt_revoked|{'retired-role-key'};witness_revoked=witness_revoked|{'retired-role-key'}
    args['receipt_trust']=replace(receipt_trust,public_keys=receipt_keys,revoked_key_ids=receipt_revoked)
    args['witness_trust']=replace(witness_trust,keys=witness_keys,revoked=witness_revoked)
    with pytest.raises(WitnessHold,match='shared signing key material'):
        verify_independent_witness(**args)

def test_equal_key_names_in_distinct_authorities_do_not_replace_material_comparison():
    witness_private,args=fixture();identifier=args['receipt']['key_id']
    args['witness']['key_id']=identifier
    args['witness_trust']=replace(args['witness_trust'],keys={identifier:raw_public(witness_private)})
    resign(witness_private,args['witness'])
    decision=verify_independent_witness(**args)
    assert decision['witness_independent_key_domain'] is True
    assert decision['dispatch_authorized'] is False
    assert decision['worker_execution_authorized'] is False

def test_distinct_test_signers_still_do_not_establish_external_authority():
    _,args=fixture();decision=verify_independent_witness(**args)
    for key in ('externally_current_highwater_verified','witness_currentness_authenticated_from_live_service',
                'global_nonce_consumption_verified','remote_cas_receipt_independently_verified',
                'owner_scope_epoch_mapping_verified','native_worker_side_effect_fencing_verified',
                'dispatch_authorized','worker_execution_authorized'):
        assert decision[key] is False
