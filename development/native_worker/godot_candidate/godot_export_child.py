"""Headless export child inside the existing AtomicProcess Job Object.

No scheduler, credentials, signing, GUI or retry. Parent retains job-tree cleanup.
"""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
MAX_PLAN_BYTES=2*1024*1024

def read_plan_bytes(path):
 with Path(path).open('rb') as stream:raw=stream.read(MAX_PLAN_BYTES+1)
 if not 0<len(raw)<=MAX_PLAN_BYTES:raise ValueError('FROZEN_PLAN_SIZE_BOUND')
 return raw
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def environment(stage,engine):
 stage=Path(stage);env={'PATH':str(Path(engine).parent),'USERPROFILE':str(stage/'profile'),'HOME':str(stage/'profile'),'APPDATA':str(stage/'profile/AppData/Roaming'),'LOCALAPPDATA':str(stage/'profile/AppData/Local'),'TEMP':str(stage/'tmp'),'TMP':str(stage/'tmp')}
 for key in ('SystemRoot','WINDIR'):
  if key in os.environ:env[key]=os.environ[key]
 return env
def output_path(stage,plan):
 name=plan['output_name'] if plan.get('schema')=='OpenRemaster.GodotDevBuildPlan.v2' else 'game.exe'
 if type(name) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.exe',name) or name.lower().endswith('.console.exe'):raise ValueError('OUTPUT_NAME')
 if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:raise ValueError('OUTPUT_DEVICE_NAME')
 return Path(stage)/'export'/name
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--project',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 raw=read_plan_bytes(a.plan)
 if hashlib.sha256(raw).hexdigest()!=a.plan_sha256:raise ValueError('FROZEN_PLAN_CHANGED')
 plan=json.loads(raw);stage=Path(a.plan).resolve().parent
 project=Path(a.project).resolve();output=Path(a.output).resolve()
 if project!=stage/'source/godot' or output!=output_path(stage,plan):raise ValueError('STAGE_BOUNDARY')
 if sha(plan['engine']['path'])!=plan['engine']['sha256']:raise ValueError('ENGINE_CHANGED')
 env=environment(stage,plan['engine']['path'])
 for name in ('APPDATA','LOCALAPPDATA','TEMP'):Path(env[name]).mkdir(parents=True,exist_ok=True)
 templates=Path(env['APPDATA'])/'Godot/export_templates'/plan['engine_version'];templates.mkdir(parents=True,exist_ok=False)
 for entry in plan['templates']:
  src=Path(entry['path']);dst=templates/src.name
  if src.name not in ('windows_debug_x86_64.exe','windows_debug_x86_64_console.exe') or sha(src)!=entry['sha256']:raise ValueError('TEMPLATE_CHANGED')
  shutil.copyfile(src,dst)
  if sha(dst)!=entry['sha256']:raise ValueError('COPIED_TEMPLATE_CHANGED')
 command=[plan['engine']['path'],'--headless','--path',str(project),'--export-debug',plan['preset'],str(output)]
 result=subprocess.run(command,cwd=project,env=env,timeout=plan['timeout_seconds'],check=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 return result.returncode
if __name__=='__main__':raise SystemExit(main())
