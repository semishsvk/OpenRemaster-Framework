"""Bounded local adapter tests. Authority/process outcomes are unit doubles."""
import copy,hashlib,importlib.util,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import godot_build as g
from godot_export_child import environment
HERE=Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
@pytest.fixture
def plan(tmp_path):
 source=tmp_path/'project';source.mkdir()
 for name in ('project.godot','export_presets.cfg'):(source/name).write_bytes((HERE/'fixture'/name).read_bytes())
 engine=tmp_path/'engine.exe';engine.write_bytes(b'TEST_ENGINE_NOT_EXECUTABLE')
 template=tmp_path/'windows_debug_x86_64.exe';template.write_bytes(b'TEST_TEMPLATE_NOT_EXECUTABLE')
 value=dict(schema='OpenRemaster.GodotDevBuildPlan.v1',profile='DEV_UNSIGNED',production_go=False,project_id='SYNTHETIC',source_root=str(source),source_files=[dict(path=p.name,sha256=g.sha(p),bytes=p.stat().st_size) for p in sorted(source.iterdir())],engine=dict(path=str(engine),sha256=g.sha(engine)),engine_version='4.7.2.stable',templates=[dict(path=str(template),sha256=g.sha(template))],preset='Windows DEV',timeout_seconds=10)
 return value
def test_valid_plan_and_source_pins(plan):
 assert len(g.validate_plan(plan))==64;g.verify_sources(plan)
@pytest.mark.parametrize('bad',('../escape','/escape','C:/escape','a\\b','a/../b','a//b','a:stream','CON','nul.json','foo.','foo ','','.', './a'))
def test_lexical_source_escape_denied(bad):
 with pytest.raises(g.GodotHold):g.relative(bad)
@pytest.mark.parametrize('field,value',[('profile','PRODUCTION'),('production_go',True),('timeout_seconds',True),('timeout_seconds',2401),('preset','--editor'),('preset','bad\nname'),('engine_version','UNKNOWN')])
def test_invalid_policy_denied(plan,field,value):
 plan[field]=value
 with pytest.raises(g.GodotHold):g.validate_plan(plan)
def test_duplicate_casefold_paths_denied(plan):
 row=copy.deepcopy(plan['source_files'][0]);row['path']=row['path'].upper();plan['source_files'].append(row)
 with pytest.raises(g.GodotHold,match='SOURCE_COLLISION'):g.validate_plan(plan)
def test_changed_source_denied(plan):
 (Path(plan['source_root'])/'project.godot').write_text('CHANGED',encoding='utf-8')
 with pytest.raises(g.GodotHold,match='SOURCE_CHANGED'):g.verify_sources(plan)
def test_changed_tool_denied(plan):
 Path(plan['engine']['path']).write_bytes(b'CHANGED')
 with pytest.raises(g.GodotHold,match='TOOL_CHANGED'):g.verify_sources(plan)
def test_missing_admission_denied(plan):
 with pytest.raises(g.GodotHold,match='OWNER_RESOURCE_ADAPTER_NOT_CONNECTED'):g.validate_admission(None,'a'*32,plan,g.validate_plan(plan))
@pytest.mark.parametrize('change',[{'project_id':'FOREIGN'},{'operation_id':'b'*32},{'plan_sha256':'f'*64},{'development_execution_authorized':False},{'production_go':True},{'automatic_retry':True},{'evidence_reference':''}])
def test_admission_binding_and_hold(plan,change):
 digest=g.validate_plan(plan)
 decision=dict(operation_id='a'*32,project_id='SYNTHETIC',plan_sha256=digest,development_execution_authorized=True,production_go=False,automatic_retry=False,evidence_reference='UNIT_DOUBLE_NOT_AUTHORITY');decision.update(change)
 with pytest.raises(g.GodotHold):g.validate_admission(lambda *a:decision,'a'*32,plan,digest)
def test_environment_drops_ambient_credentials(tmp_path,monkeypatch):
 monkeypatch.setenv('AWS_SECRET_ACCESS_KEY','UNIT_DUMMY');monkeypatch.setenv('GODOT_SCRIPT_ENCRYPTION_KEY','UNIT_DUMMY');monkeypatch.setenv('NODE_OPTIONS','UNIT_DUMMY')
 env=environment(tmp_path,'C:/engine/godot.exe')
 assert not {'AWS_SECRET_ACCESS_KEY','GODOT_SCRIPT_ENCRYPTION_KEY','NODE_OPTIONS'}&env.keys()
 assert Path(env['APPDATA']).is_relative_to(tmp_path)
def test_broker_scenarios_and_request_scope():
 broker=load('godot_candidate_broker',HERE/'worker/broker.py')
 for scenario in ('build_studio_dev','build_godot_dev'):
  assert broker.validate(dict(action='submit',operation_id='a'*32,scenario=scenario))['scenario']==scenario
 for change in ({'scenario':'shell'},{'path':'C:/arbitrary'},{'admission':True}):
  req=dict(action='submit',operation_id='a'*32,scenario='build_godot_dev');req.update(change)
  with pytest.raises(ValueError):broker.validate(req)
def test_default_broker_hook_never_grants_authority():
 broker=load('godot_candidate_broker_hold',HERE/'worker/broker.py')
 with pytest.raises(ValueError,match='GODOT_OWNER_RESOURCE_ADAPTER_NOT_CONNECTED'):broker.verify_godot_admission('a'*32,'SYNTHETIC','b'*64)

def test_broker_godot_rechecks_full_inputs_before_return(monkeypatch):
 broker=load('godot_postflight_order',HERE/'worker/broker.py');events=[]
 result={'success':True}
 def execute(*args,**kwargs):
  assert kwargs['admit'] is broker.verify_godot_admission
  events.append('adapter_completed');return result
 monkeypatch.setattr(broker,'load',lambda *args:SimpleNamespace(execute=execute))
 monkeypatch.setattr(broker,'verify_inputs',lambda:events.append('full_input_pins_verified'))
 assert broker.execute_worker('a'*32,'build_godot_dev',{}) is result
 assert events==['adapter_completed','full_input_pins_verified']

@pytest.mark.parametrize('reason',['TOOLCHAIN_CHANGED:launcher_payload','OFFLINE_DEPENDENCY_CHANGED:archive','WORKER_CONFIG_PIN_CHANGED'])
def test_broker_postflight_drift_holds_without_commit_or_retry(tmp_path,monkeypatch,reason):
 broker=load('godot_postflight_hold',HERE/'worker/broker.py');calls=[]
 monkeypatch.setattr(broker,'ROOT',tmp_path)
 (tmp_path/'BUILD-PLAN.json').write_text('{}')
 (tmp_path/'GODOT-BUILD-PLAN.json').write_text('{"test":"postflight"}')
 pins={'godot_plan_sha256':broker.sha(tmp_path/'GODOT-BUILD-PLAN.json')}
 def execute(*args,**kwargs):calls.append('modeled_export');return {'success':True}
 monkeypatch.setattr(broker,'load',lambda *args:SimpleNamespace(execute=execute))
 def changed():raise ValueError(reason)
 monkeypatch.setattr(broker,'verify_inputs',changed)
 req=dict(action='submit',operation_id='a'*32,scenario='build_godot_dev')
 result=broker.submit(req,pins)
 assert result['state']=='HOLD' and result['commit'] is None
 assert result['reason']=='ValueError:'+reason and result['automatic_retry'] is False
 assert result['launch_count']==1
 replay=broker.submit(req,pins)
 assert replay['state']=='HOLD' and replay['replayed'] is True and replay['commit'] is None
 assert calls==['modeled_export']

def test_broker_does_not_mask_adapter_failure(monkeypatch):
 broker=load('godot_adapter_failure',HERE/'worker/broker.py')
 def failed(*args,**kwargs):raise ValueError('ADMISSION_REVOKED')
 monkeypatch.setattr(broker,'load',lambda *args:SimpleNamespace(execute=failed))
 monkeypatch.setattr(broker,'verify_inputs',lambda:pytest.fail('ADAPTER_FAILURE_MUST_PROPAGATE'))
 with pytest.raises(ValueError,match='ADMISSION_REVOKED'):broker.execute_worker('a'*32,'build_godot_dev',{})
def test_missing_admission_creates_no_operation(plan,tmp_path):
 root=tmp_path/'worker';root.mkdir();raw=g.canonical(plan);(root/'GODOT-BUILD-PLAN.json').write_bytes(raw)
 with pytest.raises(g.GodotHold,match='OWNER_RESOURCE_ADAPTER_NOT_CONNECTED'):g.execute(root,'a'*32,{'godot_plan_sha256':hashlib.sha256(raw).hexdigest()},lambda *a:pytest.fail('NO_LAUNCH'))
 assert not (root/'state').exists()
def test_modeled_export_and_replay_integrity(plan,tmp_path):
 root=tmp_path/'worker';root.mkdir();raw=g.canonical(plan);(root/'GODOT-BUILD-PLAN.json').write_bytes(raw);(root/'TOOLS.json').write_text(json.dumps({'paths':{'python':sys.executable}}));(root/'SOURCE-INPUTS.json').write_text('{}')
 calls=[]
 class Owned:
  pid=123;returncode=0;tree_stopped=True
  def __init__(self,command,cwd,out,err,**kw):
   calls.append(command);assert command[1:3]==['-B','-I'] and kw['headless'] is True
   (root/'state/operations'/('a'*32)/'export/game.exe').write_bytes(b'MZ_UNIT_MODEL_NOT_REAL_GODOT')
  def __enter__(self):return self
  def __exit__(self,*args):return None
  def poll(self):return 0
 digest=g.validate_plan(plan)
 admit=lambda *a:dict(operation_id='a'*32,project_id='SYNTHETIC',plan_sha256=digest,development_execution_authorized=True,production_go=False,automatic_retry=False,evidence_reference='UNIT_DOUBLE_NOT_AUTHORITY')
 result=g.execute(root,'a'*32,{'godot_plan_sha256':hashlib.sha256(raw).hexdigest()},lambda *a:SimpleNamespace(AtomicProcess=Owned),admit=admit)
 saved=dict(operation_id='a'*32,worker=result,commit={'worker_result_sha256':hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()})
 assert g.verify_saved(saved) is saved and len(calls)==1
 (Path(result['stage'])/'export/game.exe').write_bytes(b'MZ_CHANGED')
 with pytest.raises(g.GodotHold,match='SAVED_GODOT_ARTIFACT_CHANGED'):g.verify_saved(saved)
def test_queue_keeps_scenario_and_refuses_operation_reuse(tmp_path,monkeypatch):
 host=load('godot_candidate_host',HERE/'worker/host.py')
 monkeypatch.setattr(host,'ROOT',tmp_path);monkeypatch.setattr(host,'STATE',tmp_path/'host-state');monkeypatch.setattr(host,'CANDIDATE',tmp_path)
 monkeypatch.setattr(host,'health',lambda:{'healthy':True});host.setup()
 result=host.submit('a'*32,'build_godot_dev');assert result['scenario']=='build_godot_dev'
 pending=json.loads((host.STATE/'pending'/('a'*32+'.json')).read_text());assert pending['scenario']=='build_godot_dev'
 with pytest.raises(ValueError,match='OPERATION_SCENARIO_CONFLICT'):host.submit('a'*32,'build_studio_dev')
def test_simulated_reparse_metadata_rejected(tmp_path,monkeypatch):
 p=tmp_path/'ordinary';p.write_bytes(b'x')
 monkeypatch.setattr(g.stat,'S_ISLNK',lambda mode:True)
 with pytest.raises(g.GodotHold,match='LINK_OR_REPARSE_FORBIDDEN'):g.regular(p)
def test_admission_expired_during_preflight_stops_before_process(plan,tmp_path):
 root=tmp_path/'worker';root.mkdir();raw=g.canonical(plan);(root/'GODOT-BUILD-PLAN.json').write_bytes(raw);(root/'TOOLS.json').write_text(json.dumps({'paths':{'python':sys.executable}}))
 calls=[]
 def admit(*args):
  calls.append(args)
  return dict(operation_id='a'*32,project_id='SYNTHETIC',plan_sha256=g.validate_plan(plan),development_execution_authorized=len(calls)==1,production_go=False,automatic_retry=False,evidence_reference='UNIT_DOUBLE')
 def load_model(*args):return SimpleNamespace(AtomicProcess=lambda *a,**k:pytest.fail('EXPIRED_ADMISSION_MUST_NOT_LAUNCH'))
 with pytest.raises(g.GodotHold,match='DEV_ADMISSION_HOLD'):g.execute(root,'a'*32,{'godot_plan_sha256':hashlib.sha256(raw).hexdigest()},load_model,admit=admit)
 assert len(calls)==2 and not (root/'state/operations'/('a'*32)/'launch.json').exists()
def test_godot_packet_must_have_project_scoped_native_binding():
 rust=(HERE/'dev_worker.rs').read_text(encoding='utf-8')
 assert 'GODOT_PROJECT_SCOPED_PACKET_REQUIRED' in rust and 'DEV_UNSIGNED_GODOT_BUILD' in rust
 assert 'GODOT_PROJECT_PIN_REQUIRED' in rust and 'GODOT_SOURCE_PIN_REQUIRED' in rust
def test_client_defaults_keep_studio_and_allow_named_godot():
 for p in (HERE/'worker/dev-worker.ps1',HERE/'dev-build.ps1'):
  text=p.read_text(encoding='utf-8');assert "$Scenario='build_studio_dev'" in text and "'build_godot_dev'" in text
@pytest.mark.parametrize('invalid_return',[False,True])
def test_default_remote_godot_denial_happens_before_queue_setup(monkeypatch,capsys,invalid_return):
 broker=load('godot_prequeue_test',HERE/'worker/broker.py')
 monkeypatch.setattr(broker,'verify_runtime',lambda:None);monkeypatch.setattr(broker,'verify_inputs',lambda:{})
 def only_adapter(path,name):
  assert path.name=='godot_build.py'
  return SimpleNamespace(read_plan=lambda *a:({'project_id':'SYNTHETIC'},'a'*64),validate_admission=g.validate_admission)
 monkeypatch.setattr(broker,'load',only_adapter)
 monkeypatch.setattr(sys,'argv',['broker.py','--request',json.dumps(dict(action='submit',operation_id='a'*32,scenario='build_godot_dev'))])
 broker.main();result=json.loads(capsys.readouterr().out)
 assert result['state']=='DENIED' and 'GODOT_OWNER_RESOURCE_ADAPTER_NOT_CONNECTED' in result['reason']
 monkeypatch.setattr(broker,'verify_godot_admission',lambda *a:invalid_return)
 broker.main();result=json.loads(capsys.readouterr().out)
 assert result['state']=='DENIED' and 'ADMISSION_BINDING' in result['reason']
