"""Exercise child CLI with an intercepted process call, never a real engine."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import godot_build as g
import godot_export_child as child
from test_godot_build import plan

@pytest.fixture
def setup_child(plan,tmp_path,monkeypatch):
 stage=tmp_path/'stage';project=stage/'source/godot';project.mkdir(parents=True)
 (stage/'export').mkdir();output=stage/'export/game.exe'
 for row in plan['source_files']:shutil.copyfile(Path(plan['source_root'])/row['path'],project/row['path'])
 frozen=stage/'godot-plan.json';raw=g.canonical(plan);frozen.write_bytes(raw)
 argv=['child','--plan',str(frozen),'--plan-sha256',hashlib.sha256(raw).hexdigest(),
       '--project',str(project),'--output',str(output)]
 monkeypatch.setattr(sys,'argv',argv)
 calls=[]
 def intercepted(command,**kwargs):calls.append((command,kwargs));return SimpleNamespace(returncode=0)
 monkeypatch.setattr(child.subprocess,'run',intercepted)
 return plan,stage,project,output,frozen,argv,calls

@pytest.mark.parametrize('code',[0,7])
def test_child_uses_exact_pinned_headless_command_and_clean_environment(setup_child,monkeypatch,code):
 plan,stage,project,output,frozen,argv,calls=setup_child
 monkeypatch.setenv('AWS_SECRET_ACCESS_KEY','UNIT_DUMMY');monkeypatch.setenv('GODOT_SCRIPT_ENCRYPTION_KEY','UNIT_DUMMY')
 def intercepted(command,**kwargs):calls.append((command,kwargs));return SimpleNamespace(returncode=code)
 monkeypatch.setattr(child.subprocess,'run',intercepted)
 assert child.main()==code and len(calls)==1
 command,kwargs=calls[0]
 assert command==[plan['engine']['path'],'--headless','--path',str(project),'--export-debug',plan['preset'],str(output)]
 assert kwargs['cwd']==project and kwargs['timeout']==plan['timeout_seconds']
 assert not {'AWS_SECRET_ACCESS_KEY','GODOT_SCRIPT_ENCRYPTION_KEY'}&kwargs['env'].keys()
 assert Path(kwargs['env']['APPDATA']).is_relative_to(stage)
 assert g.sha(Path(kwargs['env']['APPDATA'])/'Godot/export_templates'/plan['engine_version']/'windows_debug_x86_64.exe')==plan['templates'][0]['sha256']

@pytest.mark.parametrize('flag',['--project','--output'])
def test_cli_cannot_redirect_outside_operation_stage(setup_child,flag):
 plan,stage,project,output,frozen,argv,calls=setup_child
 argv[argv.index(flag)+1]=str(stage.parent/'foreign')
 with pytest.raises(ValueError,match='STAGE_BOUNDARY'):child.main()
 assert not calls and not (stage/'profile').exists()

def test_changed_frozen_recipe_is_rejected_before_any_launch(setup_child):
 plan,stage,project,output,frozen,argv,calls=setup_child;frozen.write_bytes(frozen.read_bytes()+b' ')
 with pytest.raises(ValueError,match='FROZEN_PLAN_CHANGED'):child.main()
 assert not calls and not (stage/'profile').exists()

def test_changed_engine_is_rejected_before_profile_preparation(setup_child):
 plan,stage,project,output,frozen,argv,calls=setup_child;Path(plan['engine']['path']).write_bytes(b'CHANGED_NON_EXECUTABLE')
 with pytest.raises(ValueError,match='ENGINE_CHANGED'):child.main()
 assert not calls and not (stage/'profile').exists()

def test_changed_template_is_rejected_before_launch(setup_child):
 plan,stage,project,output,frozen,argv,calls=setup_child;Path(plan['templates'][0]['path']).write_bytes(b'CHANGED_TEMPLATE')
 with pytest.raises(ValueError,match='TEMPLATE_CHANGED'):child.main()
 assert not calls

def test_corrupted_staged_template_is_rejected_before_launch(setup_child,monkeypatch):
 plan,stage,project,output,frozen,argv,calls=setup_child
 monkeypatch.setattr(child.shutil,'copyfile',lambda src,dst:Path(dst).write_bytes(b'BAD_COPY'))
 with pytest.raises(ValueError,match='COPIED_TEMPLATE_CHANGED'):child.main()
 assert not calls

def test_child_timeout_does_not_try_another_engine(setup_child,monkeypatch):
 plan,stage,project,output,frozen,argv,calls=setup_child
 def timeout(command,**kwargs):calls.append(command);raise subprocess.TimeoutExpired(command,1)
 monkeypatch.setattr(child.subprocess,'run',timeout)
 with pytest.raises(subprocess.TimeoutExpired):child.main()
 assert len(calls)==1 and calls[0][0]==plan['engine']['path']

def test_reused_stage_does_not_reexecute_export(setup_child):
 plan,stage,project,output,frozen,argv,calls=setup_child
 assert child.main()==0
 with pytest.raises(FileExistsError):child.main()
 assert len(calls)==1

@pytest.mark.parametrize('reader',[g.read_plan_bytes,child.read_plan_bytes],ids=['parent','child'])
def test_oversize_recipe_read_is_bounded_before_parsing(tmp_path,monkeypatch,reader):
 path=tmp_path/'large.json';path.write_bytes(b' '*(2*1024*1024+64));original=Path.open;reads=[]
 class Reader:
  def __init__(self,stream):self.stream=stream
  def __enter__(self):self.stream.__enter__();return self
  def __exit__(self,*args):return self.stream.__exit__(*args)
  def read(self,size=-1):
   assert 0<size<=2*1024*1024+1,'UNBOUNDED_READ_FORBIDDEN';reads.append(size);return self.stream.read(size)
 def opened(self,*args,**kwargs):
  stream=original(self,*args,**kwargs);return Reader(stream) if self==path else stream
 monkeypatch.setattr(Path,'open',opened)
 with pytest.raises(ValueError,match='PLAN_SIZE_BOUND'):reader(path)
 assert reads==[2*1024*1024+1]

def test_oversize_child_cli_plan_is_rejected_before_launch(setup_child):
 plan,stage,project,output,frozen,argv,calls=setup_child;frozen.write_bytes(b' '*(2*1024*1024+1))
 with pytest.raises(ValueError,match='FROZEN_PLAN_SIZE_BOUND'):child.main()
 assert not calls and not (stage/'profile').exists()

def test_oversize_saved_recipe_is_rejected_before_artifact_loading(tmp_path):
 frozen=tmp_path/'godot-plan.json';frozen.write_bytes(b' '*(2*1024*1024+1))
 result=dict(worker=dict(stage=str(tmp_path),artifacts=dict(schema='OpenRemaster.GodotDevArtifacts.v1',
             profile='DEV_UNSIGNED',production_go=False,completion_admission_evidence='UNIT_ONLY',plan_sha256=g.sha(frozen))))
 with pytest.raises(g.GodotHold,match='PLAN_SIZE_BOUND'):g.verify_saved(result)
