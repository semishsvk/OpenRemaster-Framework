"""Headless export child inside the existing AtomicProcess Job Object.

No scheduler, credentials, signing, GUI or retry. Parent retains job-tree cleanup.
"""
import argparse,hashlib,json,os,re,shutil,stat,subprocess
from pathlib import Path,PurePosixPath
MAX_PLAN_BYTES=2*1024*1024

def _local_path(value):
 # Syntax veto before any filesystem access; not physical-drive/token attestation.
 if not isinstance(value,(str,Path)) or '\x00' in str(value):raise ValueError('LOCAL_DRIVE_PATH_REQUIRED')
 path=Path(value)
 if (not path.is_absolute() or len(path.drive)!=2 or path.drive[1]!=':'
     or path.drive[0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
     or path.root!='\\' or '..' in path.parts):raise ValueError('LOCAL_DRIVE_PATH_REQUIRED')
 for part in path.parts[1:]:
  if not part or part.endswith(('.', ' ')) or ':' in part:raise ValueError('LOCAL_DRIVE_PATH_REQUIRED')
 return path

def _fixed_drive_path(value):
 # Reuse the Win32 drive classification already exercised by probe91/92.
 # A current veto only: not immutable namespace, runtime custody or admission.
 path=_local_path(value)
 if os.name!='nt':raise ValueError('LOCAL_DRIVE_QUERY_UNAVAILABLE')
 import ctypes
 try:
  query=ctypes.WinDLL('kernel32',use_last_error=True).GetDriveTypeW
  query.argtypes=[ctypes.c_wchar_p];query.restype=ctypes.c_uint32
  kind=query(path.anchor)
 except (OSError,AttributeError,TypeError,ValueError):
  raise ValueError('LOCAL_DRIVE_QUERY_UNAVAILABLE') from None
 if type(kind) is not int or kind!=3:raise ValueError('LOCAL_FIXED_DRIVE_REQUIRED')
 return path

def _verified_chunks(value,maximum=None):
 # Same existing path/identity veto, extended to frozen plan and tool reads.
 # Observations do not retain Native file pins or establish runtime admission.
 path=_fixed_drive_path(value);before=_staged_regular(path)
 if maximum is not None and not 0<before.st_size<=maximum:raise ValueError('FROZEN_PLAN_SIZE_BOUND')
 key=lambda info:(info.st_dev,info.st_ino,info.st_nlink,info.st_size,info.st_mtime_ns)
 try:
  count=0
  with path.open('rb') as source:
   if key(os.fstat(source.fileno()))!=key(before):raise ValueError('EXPORT_INPUT_CHANGED')
   for block in iter(lambda:source.read(1048576),b''):
    count+=len(block)
    if count>before.st_size:raise ValueError('EXPORT_INPUT_CHANGED')
    yield block
   after=os.fstat(source.fileno())
  current=_staged_regular(path)
  if count!=before.st_size or key(after)!=key(before) or key(current)!=key(before):raise ValueError('EXPORT_INPUT_CHANGED')
 except OSError:raise ValueError('EXPORT_INPUT_UNAVAILABLE') from None

def read_plan_bytes(path):
 return b''.join(_verified_chunks(path,MAX_PLAN_BYTES))

def sha(path):
 h=hashlib.sha256()
 for chunk in _verified_chunks(path):h.update(chunk)
 return h.hexdigest()

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

def environment(stage,engine):
 stage=_local_path(stage);engine=_local_path(engine);env={'PATH':str(Path(engine).parent),'USERPROFILE':str(stage/'profile'),'HOME':str(stage/'profile'),'APPDATA':str(stage/'profile/AppData/Roaming'),'LOCALAPPDATA':str(stage/'profile/AppData/Local'),'TEMP':str(stage/'tmp'),'TMP':str(stage/'tmp')}
 env.update(_windows_bootstrap_environment())
 return env
def output_path(stage,plan):
 name=plan['output_name'] if plan.get('schema')=='OpenRemaster.GodotDevBuildPlan.v2' else 'game.exe'
 if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.exe',name) or name.lower().endswith('.console.exe'):raise ValueError('OUTPUT_NAME')
 if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:raise ValueError('OUTPUT_DEVICE_NAME')
 return Path(stage)/'export'/name
def _staged_regular(path,directory=False):
 try:
  for current in (path,*path.parents):
   info=current.lstat()
   if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:raise ValueError('STAGED_SOURCE_REPARSE')
   expected_dir=current!=path or directory
   if not (stat.S_ISDIR(info.st_mode) if expected_dir else stat.S_ISREG(info.st_mode)):raise ValueError('STAGED_SOURCE_KIND')
   if current==path:result=info
  if not directory and (result.st_nlink!=1 or result.st_ino<=0):raise ValueError('STAGED_SOURCE_FILE_IDENTITY')
  return result
 except OSError:raise ValueError('STAGED_SOURCE_UNAVAILABLE') from None

def _verify_staged_sources(project,plan):
 # Detection immediately before export, never immutable namespace/owner custody.
 project=_fixed_drive_path(project);_staged_regular(project,True)
 rows=plan.get('source_files');seen=set();total=0;checked=[]
 if type(rows) is not list or not 2<=len(rows)<=10000:raise ValueError('STAGED_SOURCE_CLOSURE')
 for row in rows:
  if type(row) is not dict or set(row)!={'path','sha256','bytes'}:raise ValueError('STAGED_SOURCE_ENTRY')
  value=row['path']
  if type(value) is not str or not 0<len(value)<=240 or '\\' in value:raise ValueError('STAGED_SOURCE_PATH')
  relative=PurePosixPath(value)
  if (not relative.parts or relative.is_absolute() or relative.as_posix()!=value
      or any(part in ('.','..') or ':' in part or '\x00' in part or part.endswith(('.', ' ')) for part in relative.parts)):
   raise ValueError('STAGED_SOURCE_PATH')
  if any(re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',part) for part in relative.parts):raise ValueError('STAGED_SOURCE_PATH')
  if value.casefold() in seen:raise ValueError('STAGED_SOURCE_COLLISION')
  seen.add(value.casefold())
  if (type(row['bytes']) is not int or not 0<=row['bytes']<=64*1024*1024
      or type(row['sha256']) is not str or not re.fullmatch('[a-f0-9]{64}',row['sha256'])):raise ValueError('STAGED_SOURCE_ENTRY')
  total+=row['bytes'];checked.append((project/value,row))
 if total>512*1024*1024 or not {'project.godot','export_presets.cfg'}<=seen:raise ValueError('STAGED_SOURCE_CLOSURE')
 key=lambda info:(info.st_dev,info.st_ino,info.st_nlink,info.st_size,info.st_mtime_ns)
 for path,row in checked:
  before=_staged_regular(path)
  if before.st_size!=row['bytes']:raise ValueError('STAGED_SOURCE_CHANGED')
  try:
   digest=hashlib.sha256();count=0
   with path.open('rb') as source:
    opened=os.fstat(source.fileno())
    if key(opened)!=key(before):raise ValueError('STAGED_SOURCE_CHANGED')
    for block in iter(lambda:source.read(1048576),b''):
     count+=len(block)
     if count>row['bytes']:raise ValueError('STAGED_SOURCE_CHANGED')
     digest.update(block)
    after=os.fstat(source.fileno())
   current=_staged_regular(path)
   if key(before)!=key(after) or key(before)!=key(current) or count!=row['bytes'] or digest.hexdigest()!=row['sha256']:raise ValueError('STAGED_SOURCE_CHANGED')
  except OSError:raise ValueError('STAGED_SOURCE_UNAVAILABLE') from None

def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--project',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 raw=read_plan_bytes(a.plan)
 if hashlib.sha256(raw).hexdigest()!=a.plan_sha256:raise ValueError('FROZEN_PLAN_CHANGED')
 plan=json.loads(raw)
 if type(plan) is not dict or plan.get('profile')!='DEV_UNSIGNED' or plan.get('production_go') is not False:raise ValueError('DEV_PLAN_REQUIRED')
 if plan.get('engine_version')!='4.7.2.stable':raise ValueError('ENGINE_VERSION_NOT_QUALIFIED')
 if type(plan.get('timeout_seconds')) is not int or not 1<=plan['timeout_seconds']<=2400:raise ValueError('TIMEOUT_BOUND')
 stage=_fixed_drive_path(a.plan).resolve().parent
 project=_fixed_drive_path(a.project).resolve();output=_fixed_drive_path(a.output).resolve()
 if project!=stage/'source/godot' or output!=output_path(stage,plan):raise ValueError('STAGE_BOUNDARY')
 _fixed_drive_path(plan['source_root'])
 for entry in (plan['engine'],*plan['templates']):
  if type(entry) is not dict or type(entry.get('path')) is not str:raise ValueError('TOOL_PIN')
  _fixed_drive_path(entry['path'])
 if sha(plan['engine']['path'])!=plan['engine']['sha256']:raise ValueError('ENGINE_CHANGED')
 names=[Path(entry['path']).name for entry in plan['templates']]
 if len(names)!=len({name.casefold() for name in names}):raise ValueError('TEMPLATE_DESTINATION_COLLISION')
 _verify_staged_sources(_fixed_drive_path(a.project),plan)
 env=environment(stage,plan['engine']['path'])
 for name in ('APPDATA','LOCALAPPDATA','TEMP'):Path(env[name]).mkdir(parents=True,exist_ok=True)
 templates=Path(env['APPDATA'])/'Godot/export_templates'/plan['engine_version'];templates.mkdir(parents=True,exist_ok=False)
 for entry in plan['templates']:
  src=Path(entry['path']);dst=templates/src.name
  if src.name not in ('windows_debug_x86_64.exe','windows_debug_x86_64_console.exe') or sha(src)!=entry['sha256']:raise ValueError('TEMPLATE_CHANGED')
  with src.open('rb') as source,dst.open('xb') as destination:shutil.copyfileobj(source,destination)
  if sha(dst)!=entry['sha256']:raise ValueError('COPIED_TEMPLATE_CHANGED')
 command=[plan['engine']['path'],'--headless','--path',str(project),'--export-debug',plan['preset'],str(output)]
 result=subprocess.run(command,cwd=project,env=env,timeout=plan['timeout_seconds'],check=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 return result.returncode
if __name__=='__main__':raise SystemExit(main())
