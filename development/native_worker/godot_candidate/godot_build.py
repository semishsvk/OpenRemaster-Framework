"""Named Godot export adapter for the existing DEV broker, never a scheduler.

The caller retains its writer lock, durable operation and owner/resource authority.
No authority is inferred from a recipe, request, hash or worker label.
"""
from __future__ import annotations
import hashlib,json,math,os,re,shutil,stat,sys,time
from pathlib import Path,PurePosixPath

SCENARIO='build_godot_dev'
MAX_PLAN_BYTES=2*1024*1024
class GodotHold(ValueError):pass
def require(ok,why):
 if not ok:raise GodotHold(why)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1048576),b''):h.update(block)
 return h.hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def _local_path(value):
 # Syntax veto before any filesystem access; not physical-drive/token attestation.
 if not isinstance(value,(str,Path)) or '\x00' in str(value):raise GodotHold('LOCAL_DRIVE_PATH_REQUIRED')
 path=Path(value)
 if (not path.is_absolute() or len(path.drive)!=2 or path.drive[1]!=':'
     or path.drive[0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
     or path.root!='\\' or '..' in path.parts):raise GodotHold('LOCAL_DRIVE_PATH_REQUIRED')
 for part in path.parts[1:]:
  if not part or part.endswith(('.', ' ')) or ':' in part:raise GodotHold('LOCAL_DRIVE_PATH_REQUIRED')
 return path

def _fixed_drive_path(value):
 # Reuse the Win32 drive classification already exercised by probe91/92.
 # A current veto only: not immutable namespace, runtime custody or admission.
 path=_local_path(value)
 if os.name!='nt':raise GodotHold('LOCAL_DRIVE_QUERY_UNAVAILABLE')
 import ctypes
 try:
  query=ctypes.WinDLL('kernel32',use_last_error=True).GetDriveTypeW
  query.argtypes=[ctypes.c_wchar_p];query.restype=ctypes.c_uint32
  kind=query(path.anchor)
 except (OSError,AttributeError,TypeError,ValueError):
  raise GodotHold('LOCAL_DRIVE_QUERY_UNAVAILABLE') from None
 if type(kind) is not int or kind!=3:raise GodotHold('LOCAL_FIXED_DRIVE_REQUIRED')
 return path

def read_plan_bytes(path):
 with regular(Path(path)).open('rb') as stream:raw=stream.read(MAX_PLAN_BYTES+1)
 require(0<len(raw)<=MAX_PLAN_BYTES,'PLAN_SIZE_BOUND')
 return raw
def relative(value):
 require(type(value) is str and 0<len(value)<=240 and '\\' not in value,'SOURCE_PATH')
 p=PurePosixPath(value)
 require(bool(p.parts) and not p.is_absolute() and p.as_posix()==value and all(x not in ('','.','..') and ':' not in x and not x.endswith(('.',' ')) for x in p.parts),'SOURCE_PATH')
 require(all(not re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',x) for x in p.parts),'SOURCE_DEVICE_PATH')
 return p
def regular(path,root=None):
 path=_fixed_drive_path(path)
 if root is not None:root=_fixed_drive_path(root)
 if root is not None:require(path.resolve().is_relative_to(Path(root).resolve()),'PATH_ESCAPE')
 for p in (path,*path.parents):
  s=p.lstat();require(not stat.S_ISLNK(s.st_mode) and not (getattr(s,'st_file_attributes',0)&0x400),'LINK_OR_REPARSE_FORBIDDEN')
 s=path.stat();require(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'REGULAR_SINGLE_LINK_REQUIRED')
 return path
def validate_plan(plan):
 fields={'schema','profile','production_go','project_id','source_root','source_files','engine','engine_version','templates','preset','timeout_seconds'}
 require(type(plan) is dict,'PLAN_SCHEMA')
 v2=plan.get('schema')=='OpenRemaster.GodotDevBuildPlan.v2'
 if v2:fields|={'output_name','console_wrapper','resource_metadata','sidecar_pck'}
 require(set(plan)==fields,'PLAN_SCHEMA')
 require(plan['schema'] in ('OpenRemaster.GodotDevBuildPlan.v1','OpenRemaster.GodotDevBuildPlan.v2') and plan['profile']=='DEV_UNSIGNED' and plan['production_go'] is False,'DEV_PLAN_REQUIRED')
 if v2:
  require(type(plan['output_name']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.exe',plan['output_name']) and not plan['output_name'].lower().endswith('.console.exe'),'OUTPUT_NAME')
  relative(plan['output_name'])
  require(all(type(plan[k]) is bool for k in ('console_wrapper','resource_metadata','sidecar_pck')),'OUTPUT_POLICY_BOOLEAN')
 require(type(plan['project_id']) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',plan['project_id']),'PROJECT_ID')
 require(type(plan['preset']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.-]{0,127}',plan['preset']),'PRESET')
 require(type(plan['timeout_seconds']) is int and 1<=plan['timeout_seconds']<=2400,'TIMEOUT_BOUND')
 require(type(plan['source_root']) is str,'SOURCE_ROOT');_local_path(plan['source_root'])
 rows=plan['source_files'];require(type(rows) is list and 2<=len(rows)<=10000,'SOURCE_COUNT')
 seen=set();total=0
 for row in rows:
  require(type(row) is dict and set(row)=={'path','sha256','bytes'},'SOURCE_ENTRY')
  name=relative(row['path']).as_posix();require(name.casefold() not in seen,'SOURCE_COLLISION');seen.add(name.casefold())
  require(type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']),'SOURCE_DIGEST')
  require(type(row['bytes']) is int and 0<=row['bytes']<=64*1024*1024,'SOURCE_SIZE');total+=row['bytes']
 require(total<=512*1024*1024 and {'project.godot','export_presets.cfg'}<=seen,'SOURCE_CLOSURE')
 require(plan['engine_version']=='4.7.2.stable','ENGINE_VERSION_NOT_QUALIFIED')
 require(type(plan['templates']) is list and 1<=len(plan['templates'])<=2,'TEMPLATE_COUNT')
 for tool in (plan['engine'],*plan['templates']):
  require(type(tool) is dict and set(tool)=={'path','sha256'} and type(tool['path']) is str and type(tool['sha256']) is str and re.fullmatch('[0-9a-f]{64}',tool['sha256']),'TOOL_PIN')
  _local_path(tool['path'])
 names=[Path(x.get('path','')).name for x in plan['templates'] if isinstance(x,dict)]
 require(len(names)==len({name.casefold() for name in names}),'TEMPLATE_DESTINATION_COLLISION')
 require({Path(x.get('path','')).name for x in plan['templates'] if isinstance(x,dict)} in ({'windows_debug_x86_64.exe'},{'windows_debug_x86_64.exe','windows_debug_x86_64_console.exe'}),'DEBUG_TEMPLATE_SET')
 if v2 and plan['console_wrapper']:require({Path(x['path']).name for x in plan['templates']}=={'windows_debug_x86_64.exe','windows_debug_x86_64_console.exe'},'CONSOLE_TEMPLATE_PIN_REQUIRED')
 return hashlib.sha256(canonical(plan)).hexdigest()
def verify_sources(plan):
 validate_plan(plan);root=Path(plan['source_root'])
 for row in plan['source_files']:
  p=regular(root/row['path'],root)
  require(p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'SOURCE_CHANGED')
 for item in (plan['engine'],*plan['templates']):require(sha(regular(Path(item['path'])))==item['sha256'],'TOOL_CHANGED')
def validate_admission(admit,operation,plan,plan_sha):
 require(callable(admit),'OWNER_RESOURCE_ADAPTER_NOT_CONNECTED')
 # Only an existing trusted control-plane adapter may provide this decision.
 # A queue request never carries approval booleans or an authority implementation.
 decision=admit(operation,plan['project_id'],plan_sha)
 require(type(decision) is dict and decision.get('operation_id')==operation and decision.get('project_id')==plan['project_id'] and decision.get('plan_sha256')==plan_sha,'ADMISSION_BINDING')
 require(decision.get('development_execution_authorized') is True and decision.get('production_go') is False and decision.get('automatic_retry') is False,'DEV_ADMISSION_HOLD')
 require(type(decision.get('evidence_reference')) is str and bool(decision['evidence_reference']),'ADMISSION_EVIDENCE_REQUIRED')
 return decision
def output_name(plan):return plan['output_name'] if plan.get('schema')=='OpenRemaster.GodotDevBuildPlan.v2' else 'game.exe'
def artifact_records(stage,plan=None):
 out=_fixed_drive_path(stage)/'export';files=sorted(out.iterdir())
 if plan and plan.get('schema')=='OpenRemaster.GodotDevBuildPlan.v2':
  name=output_name(plan);stem=name[:-4];expected={name}
  if plan['sidecar_pck']:expected.add(stem+'.pck')
  if plan['console_wrapper']:expected.add(stem+'.console.exe')
  require({x.name for x in files}==expected,'ARTIFACT_NAMES')
 else:
  require(1<=len(files)<=2,'ARTIFACT_SET')
  require({x.name for x in files} in ({'game.exe'},{'game.exe','game.pck'}),'ARTIFACT_NAMES')
 records=[]
 for p in files:
  regular(p,out);require(0<p.stat().st_size<=512*1024*1024,'ARTIFACT_SIZE')
  if p.suffix=='.exe':
   with p.open('rb') as stream:require(stream.read(2)==b'MZ','WINDOWS_ARTIFACT_HEADER')
  records.append(dict(path=p.relative_to(stage).as_posix(),sha256=sha(p),bytes=p.stat().st_size))
 require(sum(x['bytes'] for x in records)<=512*1024*1024,'ARTIFACT_TOTAL_SIZE')
 return records
def verify_saved(result):
 stage=Path(result['worker']['stage']);artifacts=result['worker']['artifacts']
 require(artifacts.get('schema')=='OpenRemaster.GodotDevArtifacts.v1' and artifacts.get('profile')=='DEV_UNSIGNED' and artifacts.get('production_go') is False,'SAVED_GODOT_SCOPE')
 require(type(artifacts.get('completion_admission_evidence')) is str and bool(artifacts['completion_admission_evidence']),'SAVED_COMPLETION_ADMISSION_EVIDENCE_REQUIRED')
 frozen=regular(stage/'godot-plan.json',stage);raw=read_plan_bytes(frozen);require(hashlib.sha256(raw).hexdigest()==artifacts['plan_sha256'],'SAVED_RECIPE_CHANGED')
 plan,_=parse_plan_bytes(raw);require(plan['project_id']==artifacts['project_id'] and result['operation_id']==artifacts['operation_id'],'SAVED_GODOT_BINDING')
 require(artifact_records(stage,plan)==artifacts['files'],'SAVED_GODOT_ARTIFACT_CHANGED')
 require(sha(regular(stage/'artifacts.json',stage))==result['worker']['artifacts_manifest_sha256'],'SAVED_ARTIFACT_MANIFEST_CHANGED')
 require(hashlib.sha256(json.dumps(result['worker'],sort_keys=True).encode()).hexdigest()==result['commit']['worker_result_sha256'],'SAVED_COMMIT_CHANGED')
 return result
def parse_json_bytes(raw):
 # Shared strict JSON hooks for bounded recipe and tool-manifest callers.
 def unique(pairs):
  result={}
  for k,v in pairs:
   require(k not in result,'DUPLICATE_PLAN_KEY');result[k]=v
  return result
 def nonfinite(value):raise GodotHold('NONFINITE_JSON')
 def finite_float(value):
  result=float(value);require(math.isfinite(result),'NONFINITE_JSON');return result
 return json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite,parse_float=finite_float)

def parse_plan_bytes(raw):
 require(type(raw) is bytes and 0<len(raw)<=MAX_PLAN_BYTES,'PLAN_SIZE_BOUND')
 plan=parse_json_bytes(raw);return plan,validate_plan(plan)
def read_plan(root,pins):
 root=Path(root)
 raw=read_plan_bytes(root/'GODOT-BUILD-PLAN.json');require(hashlib.sha256(raw).hexdigest()==pins.get('godot_plan_sha256'),'COMMISSIONED_PLAN_PIN_REQUIRED')
 return parse_plan_bytes(raw)

def verify_python_tool(root,expected_tools_sha256):
 # Pin existing metadata through the external controller config, never its own digest.
 require(type(expected_tools_sha256) is str and re.fullmatch('[a-f0-9]{64}',expected_tools_sha256),'PYTHON_TOOLS_EXTERNAL_PIN')
 with regular(Path(root)/'TOOLS.json',root).open('rb') as stream:raw=stream.read(65537)
 require(0<len(raw)<=65536,'PYTHON_TOOLS_SIZE_BOUND')
 require(hashlib.sha256(raw).hexdigest()==expected_tools_sha256,'PYTHON_TOOLS_CHANGED')
 value=parse_json_bytes(raw)
 require(type(value) is dict and set(value)=={'paths','files'},'PYTHON_TOOLS_SCHEMA')
 paths=value['paths'];files=value['files']
 require(type(paths) is dict and 1<=len(paths)<=64 and all(type(k) is str and type(v) is str for k,v in paths.items()),'PYTHON_TOOL_PATHS')
 require(type(files) is list and 1<=len(files)<=64,'PYTHON_TOOL_FILES')
 roles=set();python=[]
 for row in files:
  require(type(row) is dict and set(row)=={'role','path','sha256'} and type(row['role']) is str
      and re.fullmatch('[A-Za-z0-9_.-]{1,128}',row['role']) and row['role'] not in roles
      and type(row['path']) is str and Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts
      and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}',row['sha256']),'PYTHON_TOOL_ENTRY')
  roles.add(row['role'])
  if row['role']=='python':python.append(row)
 require(len(python)==1 and type(paths.get('python')) is str,'PYTHON_TOOL_REQUIRED')
 selected=python[0]
 require(Path(paths['python']).is_absolute() and '..' not in Path(paths['python']).parts
     and Path(paths['python'])==Path(selected['path'])==Path(sys.executable),'PYTHON_TOOL_SELECTION_CHANGED')
 executable=regular(Path(sys.executable));limit=64*1024*1024;total=0;digest=hashlib.sha256()
 with executable.open('rb') as stream:
  while True:
   block=stream.read(min(1048576,limit-total+1))
   if not block:break
   total+=len(block);require(total<=limit,'PYTHON_BINARY_SIZE_BOUND');digest.update(block)
 require(total>0 and digest.hexdigest()==selected['sha256'],'PYTHON_BINARY_CHANGED')
 return str(executable.resolve())

def _windows_bootstrap_environment():
 # Existing export boundary only: verify supplied OS roots, never inherit them
 # by assertion alone. Missing keys retain the original explicit-omission policy.
 supplied={key:os.environ[key] for key in ('SystemRoot','WINDIR') if key in os.environ}
 if not supplied:return {}
 if os.name!='nt':raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_UNAVAILABLE')
 import ctypes,stat
 try:
  api=ctypes.WinDLL('kernel32',use_last_error=True).GetWindowsDirectoryW
  api.argtypes=[ctypes.c_wchar_p,ctypes.c_uint];api.restype=ctypes.c_uint
  buffer=ctypes.create_unicode_buffer(32768);count=api(buffer,len(buffer))
 except (OSError,AttributeError,TypeError,ValueError):
  raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_UNAVAILABLE') from None
 if type(count) is not int or not 0<count<len(buffer):raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_BOUND')
 value=buffer[:count]
 if '\x00' in value:raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_INVALID')
 path=Path(value)
 if not path.is_absolute() or str(path).startswith('\\\\') or '..' in path.parts:
  raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_INVALID')
 for part in path.parts[1:]:
  if not part or part.endswith(('.', ' ')) or ':' in part:raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_INVALID')
 try:
  for current in (path,*path.parents):
   info=current.lstat()
   if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
    raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_REPARSE_OR_KIND')
 except OSError:
  raise ValueError('EXPORT_WINDOWS_BOOTSTRAP_UNAVAILABLE') from None
 expected=os.path.normcase(os.path.normpath(value))
 for candidate in supplied.values():
  if (type(candidate) is not str or not candidate or '\x00' in candidate
      or not Path(candidate).is_absolute() or '..' in Path(candidate).parts
      or os.path.normcase(os.path.normpath(candidate))!=expected):
   raise ValueError('EXPORT_WINDOWS_ENVIRONMENT_INVALID')
 return {key:value for key in supplied}

def export_environment(stage,engine):
 # Apply the existing export profile to Python too, before it can read parent secrets.
 stage=_local_path(stage);engine=_local_path(engine)
 env={'PATH':str(engine.parent),'USERPROFILE':str(stage/'profile'),'HOME':str(stage/'profile'),
      'APPDATA':str(stage/'profile/AppData/Roaming'),'LOCALAPPDATA':str(stage/'profile/AppData/Local'),
      'TEMP':str(stage/'tmp'),'TMP':str(stage/'tmp')}
 env.update(_windows_bootstrap_environment())
 return env

def execute(root,operation,pins,load,*,admit=None,on_owned=None,phase_admit=None):
 root=Path(root);require(type(operation) is str and re.fullmatch('[a-f0-9]{32}',operation),'OPERATION_ID')
 plan,plan_sha=read_plan(root,pins);raw=read_plan_bytes(root/'GODOT-BUILD-PLAN.json')
 require(hashlib.sha256(raw).hexdigest()==pins.get('godot_plan_sha256'),'COMMISSIONED_PLAN_PIN_REQUIRED')
 def gate(phase):
  callback=admit if phase_admit is None else lambda op,project,sha:phase_admit(phase,op,project,sha)
  return validate_admission(callback,operation,plan,plan_sha)
 admission=gate('PRELAUNCH');verify_sources(plan)
 stage=root/'state/operations'/operation;stage.mkdir(parents=True,exist_ok=False)
 source=stage/'source/godot';source.mkdir(parents=True);out=stage/'export';out.mkdir()
 for row in plan['source_files']:
  dst=source/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(Path(plan['source_root'])/row['path'],dst)
  require(dst.stat().st_size==row['bytes'] and sha(dst)==row['sha256'],'STAGED_SOURCE_CHANGED')
 # Export presets are pinned source. They must target unsigned Windows exports.
 import configparser
 cfg=configparser.ConfigParser(interpolation=None,strict=True);cfg.read(source/'export_presets.cfg',encoding='utf-8')
 selected=[s for s in cfg.sections() if re.fullmatch(r'preset\.\d+',s) and cfg.get(s,'name',fallback='')==json.dumps(plan['preset'])]
 require(len(selected)==1 and cfg.get(selected[0],'platform',fallback='')=='"Windows Desktop"','WINDOWS_PRESET_REQUIRED')
 options=selected[0]+'.options'
 require(cfg.get(options,'codesign/enable',fallback='true')=='false','SIGNING_FORBIDDEN')
 v2=plan['schema']=='OpenRemaster.GodotDevBuildPlan.v2'
 metadata=plan['resource_metadata'] if v2 else False
 require(cfg.get(options,'application/modify_resources',fallback='true')==('true' if metadata else 'false'),'RESOURCE_METADATA_POLICY_MISMATCH')
 if v2:
  require(cfg.get(options,'debug/export_console_wrapper',fallback='MISSING')==('1' if plan['console_wrapper'] else '0'),'CONSOLE_WRAPPER_POLICY_MISMATCH')
  require(cfg.get(options,'binary_format/embed_pck',fallback='MISSING')==('false' if plan['sidecar_pck'] else 'true'),'PCK_POLICY_MISMATCH')
 require(all(cfg.get(options,k,fallback='""')=='""' for k in ('custom_template/debug','custom_template/release')),'CUSTOM_TEMPLATE_FORBIDDEN')
 native=load(root/'runtime/atomic_job_launcher.py','godot_owned_atomic')
 frozen_plan=stage/'godot-plan.json';frozen_plan.write_bytes(canonical(plan))
 # Reuse this controller interpreter; local metadata cannot redirect the command.
 command=[str(Path(sys.executable).resolve()),'-B','-I','-S',str(root/'godot_export_child.py'),'--plan',str(frozen_plan),'--plan-sha256',plan_sha,'--project',str(source),'--output',str(out/output_name(plan))]
 started=time.monotonic()
 with (stage/'stdout.log').open('xb') as stdout,(stage/'stderr.log').open('xb') as stderr:
  admission=gate('PRELAUNCH')
  last_admission=time.monotonic()
  with native.AtomicProcess(command,str(source),stdout,stderr,headless=True,environment=export_environment(stage,plan['engine']['path'])) as owned:
   if on_owned is not None:on_owned(operation,owned)
   launch=dict(schema='OpenRemaster.GodotDevLaunch.v1',operation_id=operation,project_id=plan['project_id'],command=command,pid=owned.pid,plan_sha256=plan_sha,admission_evidence=admission['evidence_reference'],profile='DEV_UNSIGNED',production_go=False)
   (stage/'launch.json').write_bytes(canonical(launch))
   while owned.poll() is None:
    require(time.monotonic()-started<=plan['timeout_seconds'],'GODOT_BUILD_TIMEOUT')
    require(os.fstat(stdout.fileno()).st_size+os.fstat(stderr.fileno()).st_size<=64*1024*1024,'GODOT_LOG_LIMIT')
    if time.monotonic()-last_admission>=1:
     gate('HEARTBEAT');last_admission=time.monotonic()
    time.sleep(.25)
   code=owned.returncode
 require(code==0 and owned.tree_stopped,'GODOT_EXPORT_FAILED_OR_TREE_NOT_STOPPED')
 require((stage/'stdout.log').stat().st_size+(stage/'stderr.log').stat().st_size<=64*1024*1024,'GODOT_LOG_LIMIT')
 for row in plan['source_files']:require(sha(regular(source/row['path'],source))==row['sha256'],'STAGED_SOURCE_CHANGED')
 verify_sources(plan)
 files=artifact_records(stage,plan)
 completion=gate('COMPLETION')
 artifacts=dict(schema='OpenRemaster.GodotDevArtifacts.v1',profile='DEV_UNSIGNED',production_go=False,project_id=plan['project_id'],operation_id=operation,plan_sha256=plan_sha,files=files,gui_executed=False,signing_requested=False,completion_admission_evidence=completion['evidence_reference'])
 (stage/'artifacts.json').write_bytes(canonical(artifacts))
 return dict(wrapper_exit=code,worker_state='PASS',worker_pid=owned.pid,owned_tree_stopped=True,stage=str(stage),elapsed_seconds=round(time.monotonic()-started,3),source_manifest_sha256=sha(root/'SOURCE-INPUTS.json'),build_plan_sha256=hashlib.sha256(raw).hexdigest(),stdout_sha256=sha(stage/'stdout.log'),stderr_sha256=sha(stage/'stderr.log'),artifacts=artifacts,artifacts_manifest_sha256=sha(stage/'artifacts.json'),success=True)
