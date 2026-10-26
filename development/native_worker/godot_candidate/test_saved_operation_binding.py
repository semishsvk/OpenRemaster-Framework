"""Saved-result substitution/recovery tests; no engine or real worker launch."""
import json
from types import SimpleNamespace
import pytest
from test_godot_build import load,HERE
OP='a'*32

def host_at(tmp_path,monkeypatch):
 host=load('saved_operation_host',HERE/'worker/host.py')
 monkeypatch.setattr(host,'ROOT',tmp_path);monkeypatch.setattr(host,'CANDIDATE',tmp_path)
 monkeypatch.setattr(host,'STATE',tmp_path/'host-state');host.setup()
 return host

def seed(host,scenario='build_godot_dev'):
 request=dict(operation_id=OP,scenario=scenario,state='QUEUED')
 result=dict(operation_id=OP,scenario=scenario,state='COMMITTED',production_go=False)
 host.write(host.STATE/'requests'/(OP+'.json'),request)
 host.write(host.STATE/'done'/(OP+'.json'),result)
 return request,result

@pytest.mark.parametrize('scenario',['build_studio_dev','build_godot_dev'])
def test_matching_saved_operation_reaches_existing_artifact_verifier(tmp_path,monkeypatch,scenario):
 host=host_at(tmp_path,monkeypatch);_,result=seed(host,scenario);calls=[]
 def verify(value):calls.append(value);return value
 monkeypatch.setattr(host,'broker',lambda:SimpleNamespace(validate_saved=verify))
 observed=host.external_status(OP)
 assert observed==dict(result,replayed=True) and calls==[result]

@pytest.mark.parametrize('field,value',[('operation_id','b'*32),('scenario','build_studio_dev')])
def test_swapped_saved_result_is_rejected_before_broker_or_artifacts(tmp_path,monkeypatch,field,value):
 host=host_at(tmp_path,monkeypatch);_,result=seed(host);result[field]=value
 host.write(host.STATE/'done'/(OP+'.json'),result)
 monkeypatch.setattr(host,'broker',lambda:pytest.fail('NO_BROKER_FOR_FOREIGN_RESULT'))
 with pytest.raises(ValueError,match='SAVED_QUEUE_RESULT_BINDING_CHANGED'):host.external_status(OP)
 assert host.read(host.STATE/'done'/(OP+'.json'))==result

def test_saved_result_without_original_request_is_rejected(tmp_path,monkeypatch):
 host=host_at(tmp_path,monkeypatch)
 host.write(host.STATE/'done'/(OP+'.json'),dict(operation_id=OP,scenario='build_godot_dev',state='COMMITTED'))
 monkeypatch.setattr(host,'broker',lambda:pytest.fail('NO_BROKER_WITHOUT_MARKER'))
 with pytest.raises(ValueError,match='SAVED_RESULT_REQUEST_MARKER_MISSING'):host.external_status(OP)

@pytest.mark.parametrize('marker_value',[None,{'operation_id':'b'*32,'scenario':'build_godot_dev'},
                                   {'operation_id':OP,'scenario':'shell'}],ids=['null','foreign-id','unknown-scenario'])
def test_invalid_request_marker_is_rejected_before_health_or_artifacts(tmp_path,monkeypatch,marker_value):
 host=host_at(tmp_path,monkeypatch);seed(host)
 host.write(host.STATE/'requests'/(OP+'.json'),marker_value)
 monkeypatch.setattr(host,'broker',lambda:pytest.fail('NO_BROKER_FOR_BAD_MARKER'))
 monkeypatch.setattr(host,'health',lambda:pytest.fail('NO_HEALTH_FOR_BAD_MARKER'))
 with pytest.raises(ValueError,match='REQUEST_MARKER_BINDING_CHANGED'):host.external_status(OP)

@pytest.mark.parametrize('field,value',[('operation_id','b'*32),('scenario','build_studio_dev'),('state','HOLD')])
def test_ledger_row_cannot_return_another_result(field,value):
 broker=load('saved_operation_broker',HERE/'worker/broker.py')
 result=dict(operation_id=OP,scenario='build_godot_dev',state='COMMITTED');result[field]=value
 row=(OP,'build_godot_dev','COMMITTED',1,'{}',json.dumps(result))
 with pytest.raises(ValueError,match='SAVED_LEDGER_RESULT_BINDING_CHANGED'):broker.row_response(row,True)

def recovery_host(tmp_path,monkeypatch):
 host=host_at(tmp_path,monkeypatch)
 monkeypatch.setattr(host,'identity',lambda pid:123)
 broker=load('recovery_pure_validator',HERE/'worker/broker.py')
 return host,broker

def test_recovery_refuses_foreign_operation_filename_before_dispatch(tmp_path,monkeypatch):
 host,broker=recovery_host(tmp_path,monkeypatch)
 host.write(host.STATE/'running'/(OP+'.json'),dict(action='submit',operation_id='b'*32,scenario='build_godot_dev'))
 monkeypatch.setattr(host,'broker',lambda:SimpleNamespace(validate=broker.validate,dispatch=lambda *a:pytest.fail('NO_FOREIGN_RECOVERY_DISPATCH')))
 with pytest.raises(ValueError,match='RECOVERY_REQUEST_BINDING_CHANGED'):host.daemon()
 assert not list((host.STATE/'done').iterdir())
 assert host.read(host.STATE/'heartbeat.json')['state']=='HOLD'

def test_orphan_recovery_preserves_operation_and_scenario_without_reexecution(tmp_path,monkeypatch):
 host,broker=recovery_host(tmp_path,monkeypatch);calls=[]
 host.write(host.STATE/'running'/(OP+'.json'),dict(action='submit',operation_id=OP,scenario='build_godot_dev'))
 def observe(req):calls.append(req);return dict(state='NOT_FOUND')
 monkeypatch.setattr(host,'broker',lambda:SimpleNamespace(validate=broker.validate,dispatch=observe))
 assert host.daemon()['state']=='HOLD'
 result=host.read(host.STATE/'done'/(OP+'.json'))
 assert result['state']=='HOLD' and result['operation_id']==OP and result['scenario']=='build_godot_dev'
 assert calls==[dict(action='status',operation_id=OP,scenario='build_godot_dev')]
