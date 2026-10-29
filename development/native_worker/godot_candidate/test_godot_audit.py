"""Ledger provenance regressions; export/authority are explicit unit doubles."""
from pathlib import Path
import pytest
from test_godot_build import load,HERE

def broker_at(tmp_path,monkeypatch):
 broker=load('godot_audit_candidate',HERE/'worker/broker.py')
 monkeypatch.setattr(broker,'ROOT',tmp_path)
 (tmp_path/'BUILD-PLAN.json').write_bytes(b'STUDIO_PLAN_TEST_ONLY')
 (tmp_path/'GODOT-BUILD-PLAN.json').write_bytes(b'GODOT_PLAN_TEST_ONLY')
 return broker,{'godot_plan_sha256':broker.sha(tmp_path/'GODOT-BUILD-PLAN.json')}

@pytest.mark.parametrize('scenario',['build_studio_dev','build_godot_dev'])
def test_ack_commit_and_replay_keep_selected_plan(tmp_path,monkeypatch,scenario):
 broker,pins=broker_at(tmp_path,monkeypatch);calls=[]
 expected=broker.sha(tmp_path/('GODOT-BUILD-PLAN.json' if scenario=='build_godot_dev' else 'BUILD-PLAN.json'))
 def execute(*args):calls.append(1);return dict(success=True,build_plan_sha256=expected)
 monkeypatch.setattr(broker,'execute_worker',execute)
 req=dict(action='submit',operation_id='a'*32,scenario=scenario)
 result=broker.submit(req,pins)
 assert result['state']=='COMMITTED'
 assert result['ack']['build_plan_sha256']==result['commit']['build_plan_sha256']==expected
 assert result['engine']==('unsigned-godot-dev-build' if scenario=='build_godot_dev' else 'unsigned-studio-dev-build')
 assert result['production_go'] is False and result['independent_authority'] is False
 replay=broker.submit(req,pins)
 assert replay['replayed'] is True and replay['ack']==result['ack'] and calls==[1]

def test_different_worker_plan_cannot_commit(tmp_path,monkeypatch):
 broker,pins=broker_at(tmp_path,monkeypatch)
 monkeypatch.setattr(broker,'execute_worker',lambda *a:dict(success=True,build_plan_sha256='f'*64))
 req=dict(action='submit',operation_id='a'*32,scenario='build_godot_dev')
 result=broker.submit(req,pins)
 assert result['state']=='HOLD' and result['commit'] is None and result['automatic_retry'] is False
 assert 'GODOT_RESULT_PLAN_BINDING_CHANGED' in result['reason']
 assert result['ack']['build_plan_sha256']==pins['godot_plan_sha256']

@pytest.mark.parametrize('pins',[{}, {'godot_plan_sha256':'f'*64}],ids=['missing-pin','wrong-pin'])
def test_uncommissioned_plan_is_rejected_before_ack(tmp_path,monkeypatch,pins):
 broker,_=broker_at(tmp_path,monkeypatch)
 monkeypatch.setattr(broker,'execute_worker',lambda *a:pytest.fail('NO_EXPORT_BEFORE_PIN_MATCH'))
 with pytest.raises(ValueError,match='GODOT_ACK_PLAN_PIN_MISMATCH'):
  broker.submit(dict(action='submit',operation_id='a'*32,scenario='build_godot_dev'),pins)
 with broker.database() as db:assert db.execute('SELECT COUNT(*) FROM operations').fetchone()[0]==0

@pytest.mark.parametrize('field',['ack','commit'])
def test_saved_provenance_mismatch_is_rejected_before_artifact_loading(tmp_path,monkeypatch,field):
 broker,pins=broker_at(tmp_path,monkeypatch);digest=pins['godot_plan_sha256']
 result=dict(state='COMMITTED',scenario='build_godot_dev',operation_id='a'*32,
             worker=dict(stage=str(tmp_path/'state/operations'/('a'*32)),build_plan_sha256=digest),
             ack=dict(build_plan_sha256=digest),commit=dict(build_plan_sha256=digest))
 result[field]['build_plan_sha256']='0'*64
 monkeypatch.setattr(broker,'load',lambda *a:pytest.fail('REJECT_BEFORE_ARTIFACT_LOADER'))
 with pytest.raises(ValueError,match='SAVED_GODOT_PLAN_BINDING_CHANGED'):broker.validate_saved(result)
