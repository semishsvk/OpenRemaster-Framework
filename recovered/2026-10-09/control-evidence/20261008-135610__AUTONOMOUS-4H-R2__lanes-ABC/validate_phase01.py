"""Fair sequential clean rehydration of the three NEW phase01 proofs.
A finite validation harness, not an executor service or substitute orchestrator.
Original/repeated data are kept separate. No original worktree or corpus writes.
"""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'20261008-094028__AUTONOMOUS-4H-PREFLIGHT__lanes-ABC'
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
TASKS=[
 {'project':'OpenMDK1','id':'default-varying-q','script':'verify_default_varying_q_pixels.py','report':'default-varying-q-verification.json','tests':384,'pin':'159d8a1c90bc306fe3366c5d59feb2fbd628a76369499757552951e792dc38c4'},
 {'project':'OpenStonekeep','id':'object-frame-tick','script':'verify_object_frame_tick.py','report':'object-frame-tick-verification.json','tests':27,'pin':'ccaedec61eea4e63ed847826369db7f65c84f08941e3429928d78db80e776840'},
 {'project':'OpenUltima8','id':'deferred-glob','script':'verify_deferred_glob_batch.py','report':'deferred-glob-batch-verification.json','tests':779,'pin':'e395067230b0e9359338bc7cf6c2889eb99a811665be211fb2a315c017b5b39f'}]

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
  if t['project']=='OpenUltima8':
   old_receipt=Path(old['output_ownership']['OpenUltima8'])/'materialization-receipt.json'
   inputs[t['id']]['relative_fixture']={'directory':'20261008-094213__AUTONOMOUS-4H__cycle01','source':str(old_receipt),'sha256':sha(old_receipt)}
 put(ROOT/'phase01-inputs.json',inputs)
 sys.path.insert(0,str(CP));from execution_journal import append_event
 results=[]
 for rep in ('phase01-clean-a','phase01-clean-b'):
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
   if not ok:put(ROOT/'phase01-failure.json',row);raise RuntimeError('PHASE01_CLEAN_REPEAT_FAILED:'+t['id'])
 if not all(sha(Path(p))==h for p,h in s['protected_inputs'].items()):raise RuntimeError('CONTROL_EPOCH_CHANGED')
 report={'schema':'OpenRemaster.FairCycleValidation.v3','run_id':s['run_id'],'phase':'R2-01','status':'PASS','mode':'INTERLEAVED',
  'checks_per_pass':1190,'checks_by_project':{t['project']:t['tests'] for t in TASKS},'results':results,
  'clean_repetitions_per_lane':2,'semantic_equivalence_excludes_only':'created_at_utc','inputs':inputs,
  'all_owned_processes_exited':True,'new_heavy_jobs':0,'new_game_jobs':0,'fidelity_verified':False,'recorded_at_utc':now().isoformat()}
 put(ROOT/'phase01-validation.json',report)
 for t in TASKS:
  lane=Path(s['output_ownership'][t['project']]);put(lane/'R2_PHASE01_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1',
   'project':t['project'],'run_id':s['run_id'],'status':'PASS','task':t['id'],'initial_report_sha256':t['pin'],
   'tests_per_pass':t['tests'],'clean_repetitions':[r for r in results if r['project']==t['project']],
   'coordinator_receipt_sha256':sha(ROOT/'phase01-validation.json'),'scope':'Original mechanism in declared synthetic input domain; no full runtime fidelity.'})
 print(json.dumps({'status':'PASS','phase':'R2-01','checks_per_pass':1190,'checks_by_project':report['checks_by_project'],'clean_repetitions_per_lane':2,
  'all_owned_processes_exited':True,'utc':report['recorded_at_utc'],'receipt_sha256':sha(ROOT/'phase01-validation.json')},indent=2))
if __name__=='__main__':main()
