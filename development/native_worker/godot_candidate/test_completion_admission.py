"""Instant modeled exports must not outrun the final owner/resource check."""
import copy,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import godot_build as g
from test_godot_build import plan
OP='a'*32

def setup_model(plan,tmp_path):
 root=tmp_path/'worker';root.mkdir();raw=g.canonical(plan)
 (root/'GODOT-BUILD-PLAN.json').write_bytes(raw)
 (root/'TOOLS.json').write_text(json.dumps({'paths':{'python':sys.executable}}))
 (root/'SOURCE-INPUTS.json').write_text('{}')
 events=[];stage=root/'state/operations'/OP
 class Owned:
  pid=789;returncode=0;tree_stopped=True
  def __init__(self,*args,**kwargs):
   events.append('modeled-process');(stage/'export/game.exe').write_bytes(b'MZ_UNIT_NOT_EXECUTABLE')
  def __enter__(self):return self
  def __exit__(self,*args):events.append('owned-context-closed')
  def poll(self):return 0
 def allowed():return dict(operation_id=OP,project_id=plan['project_id'],plan_sha256=g.validate_plan(plan),
                           development_execution_authorized=True,production_go=False,automatic_retry=False,
                           evidence_reference='UNIT_DOUBLE_COMPLETION_NOT_AUTHORITY')
 return root,stage,events,lambda *args:SimpleNamespace(AtomicProcess=Owned),allowed

@pytest.mark.parametrize('change',[
 {'development_execution_authorized':False},{'project_id':'FOREIGN'}, {'operation_id':'b'*32},
 {'plan_sha256':'f'*64},{'production_go':True},{'automatic_retry':True},{'evidence_reference':''}])
def test_revoked_or_invalid_final_admission_prevents_manifest(plan,tmp_path,change):
 root,stage,events,loader,allowed=setup_model(plan,tmp_path);checks=[]
 def admit(*args):
  checks.append(1);value=allowed()
  if len(checks)==3:value.update(change)
  return value
 with pytest.raises(g.GodotHold):
  g.execute(root,OP,{'godot_plan_sha256':g.sha(root/'GODOT-BUILD-PLAN.json')},loader,admit=admit)
 assert len(checks)==3 and events==['modeled-process','owned-context-closed']
 assert (stage/'export/game.exe').exists() and not (stage/'artifacts.json').exists()

def test_unavailable_authority_at_completion_does_not_fall_back(plan,tmp_path):
 root,stage,events,loader,allowed=setup_model(plan,tmp_path);checks=[]
 def admit(*args):
  checks.append(1)
  if len(checks)==3:raise RuntimeError('UNIT_AUTHORITY_UNAVAILABLE')
  return allowed()
 with pytest.raises(RuntimeError,match='UNIT_AUTHORITY_UNAVAILABLE'):
  g.execute(root,OP,{'godot_plan_sha256':g.sha(root/'GODOT-BUILD-PLAN.json')},loader,admit=admit)
 assert len(checks)==3 and events.count('modeled-process')==1
 assert not (stage/'artifacts.json').exists()

def test_completion_evidence_is_recorded_after_outputs_are_verified(plan,tmp_path,monkeypatch):
 root,stage,events,loader,allowed=setup_model(plan,tmp_path);checks=[]
 original=g.artifact_records
 def outputs(*args):
  rows=original(*args);events.append('outputs-verified');return rows
 monkeypatch.setattr(g,'artifact_records',outputs)
 def admit(*args):
  checks.append(1);value=allowed();value['evidence_reference']='UNIT_CHECK_'+str(len(checks))
  if len(checks)==3:
   assert events[-1]=='outputs-verified' and not (stage/'artifacts.json').exists()
  return value
 result=g.execute(root,OP,{'godot_plan_sha256':g.sha(root/'GODOT-BUILD-PLAN.json')},loader,admit=admit)
 assert len(checks)==3 and result['artifacts']['completion_admission_evidence']=='UNIT_CHECK_3'
 assert json.loads((stage/'artifacts.json').read_bytes())==result['artifacts']

@pytest.mark.parametrize('reference',[None,'',False])
def test_saved_result_without_completion_evidence_is_not_accepted(tmp_path,reference):
 result=dict(worker=dict(stage=str(tmp_path),artifacts=dict(schema='OpenRemaster.GodotDevArtifacts.v1',
             profile='DEV_UNSIGNED',production_go=False,completion_admission_evidence=reference)))
 with pytest.raises(g.GodotHold,match='SAVED_COMPLETION_ADMISSION_EVIDENCE_REQUIRED'):g.verify_saved(result)
