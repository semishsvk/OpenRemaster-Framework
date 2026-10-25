"""Fair sequential clean rehydration of the three NEW phase02 proofs.
A finite validation harness, not an executor service or substitute orchestrator.
Original/repeated data are kept separate. No original worktree or corpus writes.
"""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'20261008-094028__AUTONOMOUS-4H-PREFLIGHT__lanes-ABC'
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
TASKS=[{'id': 'wrapped-source-pixels',
  'pin': 'd8bad5e2184197ecc87ad32ac97d9434723418a6f5c5a2d7524672dab2d84b68',
  'project': 'OpenMDK1',
  'report': 'wrapped-source-pixel-verification.json',
  'script': 'verify_wrapped_source_pixels.py',
  'tests': 640},
 {'id': 'frame-prefix-chain',
  'pin': '8a90012134c0eb018e9f8d64d88964e64f0f12c20b514cb9fd7af3d7a0f094ce',
  'project': 'OpenStonekeep',
  'report': 'frame-prefix-chain-verification-v2.json',
  'script': 'verify_frame_prefix_chain_v2.py',
  'tests': 197},
 {'id': 'holding-world-placement',
  'pin': '200af772c3365efda62ef9e606a8f5b2e5492be671df3ed82aaecf7bbd16916e',
  'project': 'OpenUltima8',
  'report': 'holding-world-placement-verification.json',
  'script': 'verify_holding_world_placement.py',
  'tests': 260}]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,sort_keys=True);f.flush();os.fsync(f.fileno())
def sem(v):return {k:x for k,x in v.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)

def closure(root,entry):
 todo=[entry];done={}
 while todo:
  n=todo.pop()
  if n in done:continue
  if len(done)>20:raise RuntimeError('MODULE_BUDGET')
  tree=ast.parse((root/n).read_text(encoding='utf-8-sig'),filename=n);done[n]=sha(root/n)
  for node in ast.walk(tree):
   mods=[node.module] if isinstance(node,ast.ImportFrom) and node.module else [m.name for m in node.names] if isinstance(node,ast.Import) else []
   for m in mods:
    f=m.split('.')[0]+'.py'
    if (root/f).is_file() and f not in done:todo.append(f)
 return done

def main():
 s=load(ROOT/'run-state.json');old=load(OLD/'run-state.json');deadline=datetime.fromisoformat(s['deadline_utc'])
 assert all(sha(Path(p))==h for p,h in s['protected_inputs'].items())
 inputs={}
 for t in TASKS:
  lane=Path(s['output_ownership'][t['project']]);r=load(lane/t['report'])
  if sha(lane/t['report'])!=t['pin']:raise RuntimeError('INITIAL_REPORT_PIN_MISMATCH:'+t['id'])
  if r['status']!='PASS' or r['tests']!=t['tests']:raise RuntimeError('INITIAL_TEST_STATUS:'+t['id'])
  inputs[t['id']]={'script_hashes':closure(lane,t['script']),'initial_report_sha256':t['pin'],'ir_files':{}}
  if t['project']=='OpenMDK1':
   old_ir=Path(old['output_ownership']['OpenMDK1']).parent/'20261008-074645__MDK1-ALIAS-ACTIVE__bounded-v1'/'material-binding-sourceir.json'
   assert sha(old_ir)=='b597a9f27d5e03b34117d02d893a6e8b456406c8d413a2dd73276e96db32e783'
   inputs[t['id']]['relative_fixture']={'directory':'20261008-074645__MDK1-ALIAS-ACTIVE__bounded-v1','source':str(old_ir),'sha256':sha(old_ir)}
 put(ROOT/'phase02-inputs.json',inputs)
 sys.path.insert(0,str(CP));from execution_journal import append_event
 results=[]
 for rep in ('phase02-clean-a','phase02-clean-b'):
  for t in TASKS:
   if (deadline-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   lane=Path(s['output_ownership'][t['project']]);base=lane/rep;base.mkdir(exist_ok=False);out=base/'task';out.mkdir()
   for n,h in inputs[t['id']]['script_hashes'].items():
    assert sha(lane/n)==h
    with (out/n).open('xb') as f:f.write((lane/n).read_bytes())
   dep=inputs[t['id']].get('relative_fixture')
   if dep:
    path=base/dep['directory'];path.mkdir();src=Path(dep['source']);assert sha(src)==dep['sha256']
    with (path/src.name).open('xb') as f:f.write(src.read_bytes())
   start=now();clock=time.monotonic();p=subprocess.Popen([sys.executable,'-B',str(out/t['script'])],cwd=out,
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   append_event(ROOT/'execution-journal.jsonl',s['run_id'],'TEST_STARTED',project=t['project'],task=t['id'],repeat=rep,pid=p.pid)
   try:stdout,stderr=p.communicate(timeout=30)
   except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=5);raise RuntimeError('OWN_BOUNDED_TEST_TIMEOUT')
   with (out/'execution.log').open('x',encoding='utf-8') as f:f.write(stdout+'\n'+stderr)
   got=load(out/t['report']) if (out/t['report']).is_file() else {};equal=sem(got)==sem(load(lane/t['report']))
   stable=all(sha(out/n)==h and sha(lane/n)==h for n,h in inputs[t['id']]['script_hashes'].items())
   ok=p.returncode==0 and got.get('status')=='PASS' and got.get('tests')==t['tests'] and equal and stable
   row={'project':t['project'],'task':t['id'],'repeat':rep,'status':'PASS' if ok else 'FAIL','tests':t['tests'],
    'pid':p.pid,'start_utc':start.isoformat(),'end_utc':now().isoformat(),'wall_seconds':time.monotonic()-clock,
    'exit_code':p.returncode,'process_exited':p.poll() is not None,'semantic_report_equal':equal,'scripts_unchanged':stable,
    'output_directory':str(out),'report_sha256':sha(out/t['report']) if (out/t['report']).is_file() else None}
   put(out/'repeat-receipt.json',row);results.append(row)
   append_event(ROOT/'execution-journal.jsonl',s['run_id'],'TEST_FINISHED',project=t['project'],task=t['id'],pid=p.pid,status=row['status'],process_exited=row['process_exited'])
   if not ok:put(ROOT/'phase02-failure.json',row);raise RuntimeError('PHASE02_CLEAN_REPEAT_FAILED:'+t['id'])
 if not all(sha(Path(p))==h for p,h in s['protected_inputs'].items()):raise RuntimeError('CONTROL_EPOCH_CHANGED')
 report={'schema':'OpenRemaster.FairCycleValidation.v3','run_id':s['run_id'],'phase':'R2-02','status':'PASS','mode':'INTERLEAVED',
  'checks_per_pass':1097,'checks_by_project':{t['project']:t['tests'] for t in TASKS},'results':results,
  'clean_repetitions_per_lane':2,'semantic_equivalence_excludes_only':'created_at_utc','inputs':inputs,
  'all_owned_processes_exited':True,'new_heavy_jobs':0,'new_game_jobs':0,'fidelity_verified':False,'recorded_at_utc':now().isoformat()}
 put(ROOT/'phase02-validation.json',report)
 for t in TASKS:
  lane=Path(s['output_ownership'][t['project']]);put(lane/'R2_PHASE02_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1',
   'project':t['project'],'run_id':s['run_id'],'status':'PASS','task':t['id'],'initial_report_sha256':t['pin'],
   'tests_per_pass':t['tests'],'clean_repetitions':[r for r in results if r['project']==t['project']],
   'coordinator_receipt_sha256':sha(ROOT/'phase02-validation.json'),'scope':'Original mechanism in declared synthetic input domain; no full runtime fidelity.'})
 print(json.dumps({'status':'PASS','phase':'R2-02','checks_per_pass':1097,'checks_by_project':report['checks_by_project'],'clean_repetitions_per_lane':2,
  'all_owned_processes_exited':True,'utc':report['recorded_at_utc'],'receipt_sha256':sha(ROOT/'phase02-validation.json')},indent=2))
if __name__=='__main__':main()
