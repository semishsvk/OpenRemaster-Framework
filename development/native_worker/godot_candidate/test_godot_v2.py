"""V2 recipe regressions: named outputs/branding, with no real engine launch."""
import copy,hashlib,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import godot_build as g
from godot_export_child import output_path
from test_godot_build import plan
@pytest.fixture
def v2(plan):
 plan.update(schema='OpenRemaster.GodotDevBuildPlan.v2',output_name='OpenAzrael-0.1.0-dev.exe',console_wrapper=True,resource_metadata=True,sidecar_pck=True)
 source=Path(plan['source_root']);preset=source/'export_presets.cfg'
 text=preset.read_text(encoding='utf-8').replace('application/modify_resources=false','application/modify_resources=true').replace('binary_format/embed_pck=true','binary_format/embed_pck=false')+'debug/export_console_wrapper=1\n'
 preset.write_text(text,encoding='utf-8')
 for row in plan['source_files']:
  p=source/row['path'];row.update(sha256=g.sha(p),bytes=p.stat().st_size)
 console=source.parent/'windows_debug_x86_64_console.exe';console.write_bytes(b'UNIT_TEMPLATE_NOT_EXECUTABLE')
 plan['templates'].append(dict(path=str(console),sha256=g.sha(console)))
 return plan
def test_v2_plan_and_named_child_output(v2,tmp_path):
 assert len(g.validate_plan(v2))==64;g.verify_sources(v2)
 assert output_path(tmp_path,v2)==tmp_path/'export/OpenAzrael-0.1.0-dev.exe'
@pytest.mark.parametrize('name',['../escape.exe','C:/escape.exe','x\\y.exe','--flag.exe','game.console.exe','NUL.exe','name.exe:ADS','a.exe/other'])
def test_named_output_cannot_escape_or_become_a_command(v2,name):
 v2['output_name']=name
 with pytest.raises(g.GodotHold):g.validate_plan(v2)
@pytest.mark.parametrize('key,value',[('console_wrapper',1),('resource_metadata','true'),('sidecar_pck',None)])
def test_recipe_flags_require_exact_booleans(v2,key,value):
 v2[key]=value
 with pytest.raises(g.GodotHold,match='OUTPUT_POLICY_BOOLEAN'):g.validate_plan(v2)
def test_console_template_must_be_pinned(v2):
 v2['templates']=v2['templates'][:1]
 with pytest.raises(g.GodotHold,match='CONSOLE_TEMPLATE_PIN_REQUIRED'):g.validate_plan(v2)
def test_v1_does_not_silently_inherit_v2_policy(v2):
 v2['schema']='OpenRemaster.GodotDevBuildPlan.v1'
 with pytest.raises(g.GodotHold,match='PLAN_SCHEMA'):g.validate_plan(v2)
def artifacts(tmp_path,plan):
 out=tmp_path/'export';out.mkdir();name=plan['output_name'];stem=name[:-4]
 for name,data in ((name,b'MZ_UNIT'),(stem+'.console.exe',b'MZ_UNIT_CONSOLE'),(stem+'.pck',b'GDPC_UNIT')):(out/name).write_bytes(data)
 return out
def test_three_named_outputs_are_all_recorded(v2,tmp_path):
 artifacts(tmp_path,v2);rows=g.artifact_records(tmp_path,v2)
 assert len(rows)==3 and {x['path'] for x in rows}=={'export/OpenAzrael-0.1.0-dev.exe','export/OpenAzrael-0.1.0-dev.console.exe','export/OpenAzrael-0.1.0-dev.pck'}
def test_unregistered_output_is_rejected(v2,tmp_path):
 out=artifacts(tmp_path,v2);(out/'unexpected.dll').write_bytes(b'UNIT')
 with pytest.raises(g.GodotHold,match='ARTIFACT_NAMES'):g.artifact_records(tmp_path,v2)
def test_expected_console_output_cannot_be_omitted(v2,tmp_path):
 out=tmp_path/'export';out.mkdir();(out/v2['output_name']).write_bytes(b'MZ_UNIT');(out/'OpenAzrael-0.1.0-dev.pck').write_bytes(b'GDPC_UNIT')
 with pytest.raises(g.GodotHold,match='ARTIFACT_NAMES'):g.artifact_records(tmp_path,v2)
def modeled(v2,tmp_path):
 root=tmp_path/'worker';root.mkdir();raw=g.canonical(v2);(root/'GODOT-BUILD-PLAN.json').write_bytes(raw)
 (root/'TOOLS.json').write_text(json.dumps({'paths':{'python':sys.executable}}));(root/'SOURCE-INPUTS.json').write_text('{}')
 calls=[]
 class Owned:
  pid=456;returncode=0;tree_stopped=True
  def __init__(self,command,cwd,out,err,**kw):
   assert kw['headless'] is True;calls.append(command)
   stage=root/'state/operations'/('a'*32);dest=stage/'export';stem=v2['output_name'][:-4]
   for name,data in ((v2['output_name'],b'MZ_UNIT_MODEL'),(stem+'.console.exe',b'MZ_UNIT_CONSOLE'),(stem+'.pck',b'GDPC_UNIT')):(dest/name).write_bytes(data)
  def __enter__(self):return self
  def __exit__(self,*args):return None
  def poll(self):return 0
 admit=lambda *a:dict(operation_id='a'*32,project_id=v2['project_id'],plan_sha256=g.validate_plan(v2),development_execution_authorized=True,production_go=False,automatic_retry=False,evidence_reference='UNIT_DOUBLE_NOT_AUTHORITY')
 result=g.execute(root,'a'*32,{'godot_plan_sha256':hashlib.sha256(raw).hexdigest()},lambda *a:SimpleNamespace(AtomicProcess=Owned),admit=admit)
 return result,calls
def test_model_preserves_original_metadata_and_named_artifact_evidence(v2,tmp_path):
 preset=Path(v2['source_root'])/'export_presets.cfg';before=preset.read_bytes()
 result,calls=modeled(v2,tmp_path)
 assert preset.read_bytes()==before and b'application/modify_resources=true' in before
 assert len(result['artifacts']['files'])==3 and calls[0][-1].endswith('OpenAzrael-0.1.0-dev.exe')
 saved=dict(operation_id='a'*32,worker=result,commit={'worker_result_sha256':hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()})
 assert g.verify_saved(saved) is saved
def test_child_independently_rejects_device_output(v2,tmp_path):
 v2['output_name']='CON.exe'
 with pytest.raises(ValueError,match='OUTPUT_DEVICE_NAME'):output_path(tmp_path,v2)
def test_recipe_pck_mismatch_remains_fail_closed(v2,tmp_path):
 preset=Path(v2['source_root'])/'export_presets.cfg';preset.write_text(preset.read_text(encoding='utf-8').replace('binary_format/embed_pck=false','binary_format/embed_pck=true'),encoding='utf-8')
 for row in v2['source_files']:
  p=Path(v2['source_root'])/row['path'];row.update(sha256=g.sha(p),bytes=p.stat().st_size)
 with pytest.raises(g.GodotHold,match='PCK_POLICY_MISMATCH'):modeled(v2,tmp_path)
