"""Finite validation harness for the three prepared evidence lanes, not a scheduler.
Sequential bounded tests in two clean directories per project. Records real owned
PIDs and exact outputs. No game, service, worker admission, live lease or source write.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'run-state.json'
TITAN=r'F:\Remaster Framework\tools\titan-ultima\venv\Scripts\python.exe'
LANES={
 'OpenMDK1':{'python':sys.executable,'files':['static_probe.py','verify_f3_contract.py','verify_depth_guard.py','verify_perspective_inputs.py'],
  'tests':[('verify_depth_guard.py','depth-guard-verification.json',37),('verify_perspective_inputs.py','perspective-input-verification.json',336)],
  'ir_files':[],'next':'Perspective gradient/width counterpart and source-to-span interpolation.'},
 'OpenStonekeep':{'python':sys.executable,'files':['source_manifest.py','le_fixups.py','verify_callback_v2.py','verify_wrapper_route.py'],
  'tests':[('verify_callback_v2.py','callback-verification.json',76),('verify_wrapper_route.py','wrapper-delta-verification.json',89)],
  'ir_files':['callback-delta-edge-ir.json'],'next':'Account for common continuation and movement/turn intention state without assuming opaque event success.'},
 'OpenUltima8':{'python':TITAN,'files':['materialize_map5_v2.py','audit_reference_divergence.py'],
  'tests':[('materialize_map5_v2.py','materialization-receipt.json',14),('audit_reference_divergence.py','reference-divergence.json',6)],
  'ir_files':['map5-instance-ir.json','map5-evidence-ir-v2.json'],'next':'Original U8 placement consumer to resolve the +0 versus +1 XY conflict, retaining confirmed multiplicity/parentage.'}}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,sort_keys=True,indent=2)
def semantic(d):return {k:v for k,v in d.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)

def main():
 state=load(STATE);deadline=datetime.fromisoformat(state['deadline_utc'])
 if now()>=deadline:raise RuntimeError('BLOCK_DEADLINE_REACHED')
 protected=state['protected_inputs']
 if any(sha(Path(p))!=h for p,h in protected.items()):raise RuntimeError('CONTROL_BASELINE_CHANGED_REVIEW_REQUIRED')
 baseline={};results=[]
 for project,cfg in LANES.items():
  p=Path(state['output_ownership'][project]);baseline[project]={'scripts':{n:sha(p/n) for n in cfg['files']},'reports':{n:sha(p/n) for _,n,_ in cfg['tests']},'ir':{n:sha(p/n) for n in cfg['ir_files']}}
  for _,report,nt in cfg['tests']:
   r=load(p/report)
   if not r['status'].startswith('PASS') or r['tests']!=nt:raise RuntimeError('UNVALIDATED_INITIAL_RESULT:'+project)
 put(ROOT/'cycle01-validation-inputs.json',baseline)
 # Fair round-robin order: each lane gets its first clean run before any lane gets the second.
 for rep in ('clean-a','clean-b'):
  for project,cfg in LANES.items():
   if (deadline-now()).total_seconds()<60:raise RuntimeError('SAFE_SHUTDOWN_RESERVE')
   lane=Path(state['output_ownership'][project]);out=lane/rep;out.mkdir(exist_ok=False)
   for filename,h in baseline[project]['scripts'].items():
    if sha(lane/filename)!=h:raise RuntimeError('SCRIPT_DRIFT')
    with (out/filename).open('xb') as f:f.write((lane/filename).read_bytes())
    if sha(out/filename)!=h:raise RuntimeError('COPY_MISMATCH')
   testrows=[]
   for script,report,nt in cfg['tests']:
    start=now();clock=time.monotonic()
    proc=subprocess.Popen([cfg['python'],'-B',str(out/script)],cwd=out,
      env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:stdout,stderr=proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
     proc.kill();stdout,stderr=proc.communicate(timeout=5)
     put(out/(script+'.timeout.json'),{'status':'BLOCKED','pid':proc.pid,'only_owned_process_terminated':True,'started_at_utc':start.isoformat()})
     raise RuntimeError('BOUNDED_TEST_TIMEOUT')
    end=now()
    with (out/(script+'.log')).open('x',encoding='utf-8') as f:f.write(stdout+'\n'+stderr)
    got=load(out/report) if (out/report).is_file() else {}
    equal=semantic(got)==semantic(load(lane/report))
    ok=proc.returncode==0 and got.get('status','').startswith('PASS') and got.get('tests')==nt and equal
    testrows.append({'script':script,'pid':proc.pid,'start_utc':start.isoformat(),'end_utc':end.isoformat(),'wall_seconds':time.monotonic()-clock,
     'exit_code':proc.returncode,'process_exited':proc.poll() is not None,'status':'PASS' if ok else 'FAIL','tests':got.get('tests'),
     'semantic_report_equal':equal,'report_sha256':sha(out/report) if (out/report).is_file() else None})
    if not ok:break
   ir_equal=all((out/n).is_file() and sha(out/n)==h for n,h in baseline[project]['ir'].items())
   scripts_unchanged=all(sha(out/n)==h and sha(lane/n)==h for n,h in baseline[project]['scripts'].items())
   ok=len(testrows)==len(cfg['tests']) and all(r['status']=='PASS' for r in testrows) and ir_equal and scripts_unchanged
   row={'project':project,'repeat':rep,'status':'PASS' if ok else 'FAIL','tests':testrows,'ir_byte_identical':ir_equal,'scripts_unchanged':scripts_unchanged}
   put(out/'repeat-receipt.json',row);results.append(row)
   if not ok:
    put(ROOT/'cycle01-repeat-failure.json',row);raise RuntimeError('CLEAN_REPEAT_FAILED')
 overall=all(r['status']=='PASS' for r in results) and all(sha(Path(p))==h for p,h in protected.items())
 for project,cfg in LANES.items():
  lane=Path(state['output_ownership'][project]);rs=[r for r in results if r['project']==project]
  receipt={'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','run_id':state['run_id'],'deadline_utc':state['deadline_utc'],
   'checkpoint':state['run_id']+'-'+project+'-C01','project':project,'status':'PASS' if overall else 'FAIL',
   'validation_scope':'BOUNDED_SOURCE_MECHANISM_OR_CROSSCHECK; NOT_FULL_RUNTIME','checks_per_pass':sum(n for _,_,n in cfg['tests']),
   'initial_pass':True,'clean_repetitions':rs,'semantic_equivalence_excludes_only':'created_at_utc','input_hashes':baseline[project],
   'runtime_fidelity_verified':False,'new_game_jobs':0,'worktree_writes':False,'source_writes':False,'live_leases_acquired':[],
   'original_placement_gate':'BLOCKED_REFERENCE_DISAGREEMENT' if project=='OpenUltima8' else None,
   'next':cfg['next'],'recorded_at_utc':now().isoformat()}
  put(lane/'CYCLE01_CHECKPOINT.json',receipt)
 summary={'schema':'OpenRemaster.FairCycleValidation.v1','run_id':state['run_id'],'status':'PASS' if overall else 'FAIL',
  'mode':'INTERLEAVED','cycle':1,'checks_per_complete_pass':558,'clean_repetitions_per_lane':2,
  'results':results,'all_owned_processes_exited':all(t['process_exited'] for r in results for t in r['tests']),
  'no_native_runtime_fidelity_claim':True,'new_heavy_jobs':0,'protected_inputs_unchanged':overall,
  'recorded_at_utc':now().isoformat(),'elapsed_seconds':(now()-datetime.fromisoformat(state['started_at_utc'])).total_seconds()}
 put(ROOT/'cycle01-validation-receipt.json',summary)
 print(json.dumps({'status':summary['status'],'mode':summary['mode'],'cycle':1,'checks_per_pass':558,'clean_repeats_per_lane':2,
  'per_lane':{p:sum(n for _,_,n in cfg['tests']) for p,cfg in LANES.items()},'all_owned_processes_exited':summary['all_owned_processes_exited'],'new_heavy_jobs':0,
  'receipt_sha256':sha(ROOT/'cycle01-validation-receipt.json'),'utc':summary['recorded_at_utc']},indent=2))
if __name__=='__main__':main()
