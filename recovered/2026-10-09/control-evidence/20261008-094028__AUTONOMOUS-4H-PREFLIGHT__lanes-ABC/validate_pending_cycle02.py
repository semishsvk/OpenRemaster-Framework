"""Complete the two pending new milestones, not the already sealed cycle01 suite.
Bounded sequential local tests; records subprocess identity and observed exit.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
CONFIG={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_gradients.py'],
  'script':'verify_perspective_gradients.py','report':'perspective-gradient-verification.json','tests':61,
  'report_pin':'ad1d2e676cfb1804d9c4946abc65690e2776d9633d4df876bfbf41579ba4b10c','input_files':[],'ir':[]},
 'OpenUltima8':{'files':['ne_glob_candidates.py','verify_original_glob.py'],
  'script':'verify_original_glob.py','report':'original-glob-verification.json','tests':794,
  'report_pin':'7b35a5a05d1852bc47bf4edbc47d8ac2319182848d4f0e2fc647cdd2fa22b3ba',
  'input_files':['materialization-receipt.json'],'ir':['original-glob-positions.json']}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,sort_keys=True)
def semantic(x):return {k:v for k,v in x.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)
def main():
 state=load(ROOT/'run-state.json');end=datetime.fromisoformat(state['deadline_utc'])
 protected=state['resume_input_hashes']
 if any(sha(Path(p))!=h for p,h in protected.items()):raise RuntimeError('REVIEWED_CONTROL_EPOCH_CHANGED')
 baselines={};rows=[]
 for project,c in CONFIG.items():
  lane=Path(state['output_ownership'][project]);r=load(lane/c['report'])
  assert sha(lane/c['report'])==c['report_pin'] and r['status']=='PASS' and r['tests']==c['tests']
  baselines[project]={n:sha(lane/n) for n in c['files']+c['input_files']+c['ir']}
 put(ROOT/'cycle02-pending-inputs.json',baselines)
 for rep in ('cycle02-clean-a','cycle02-clean-b'):
  for project,c in CONFIG.items():
   if (end-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   lane=Path(state['output_ownership'][project]);out=lane/rep;out.mkdir(exist_ok=False)
   for n in c['files']+c['input_files']:
    if sha(lane/n)!=baselines[project][n]:raise RuntimeError('SOURCE_DRIFT')
    with (out/n).open('xb') as f:f.write((lane/n).read_bytes())
   start=now();t=time.monotonic()
   p=subprocess.Popen([sys.executable,'-B',str(out/c['script'])],cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:so,se=p.communicate(timeout=30)
   except subprocess.TimeoutExpired:
    p.kill();so,se=p.communicate(timeout=5)
    put(out/'timeout.json',{'pid':p.pid,'state':'BLOCKED_TIMEOUT','only_owned_process':True});raise
   with (out/'test.log').open('x',encoding='utf-8') as f:f.write(so+'\n'+se)
   d=load(out/c['report']) if (out/c['report']).is_file() else {}
   equal=semantic(d)==semantic(load(lane/c['report']))
   ir_ok=all((out/n).exists() and sha(out/n)==baselines[project][n] for n in c['ir'])
   stable=all(sha(out/n)==baselines[project][n] and sha(lane/n)==baselines[project][n] for n in c['files']+c['input_files'])
   passed=p.returncode==0 and d.get('status')=='PASS' and d.get('tests')==c['tests'] and equal and ir_ok and stable
   row={'project':project,'repeat':rep,'tests':d.get('tests'),'pid':p.pid,'start_utc':start.isoformat(),'end_utc':now().isoformat(),'wall_seconds':time.monotonic()-t,
    'exit_code':p.returncode,'process_exited':p.poll() is not None,'status':'PASS' if passed else 'FAIL','semantic_report_equal':equal,
    'ir_byte_identical':ir_ok,'scripts_and_inputs_unchanged':stable,'report_sha256':sha(out/c['report']) if (out/c['report']).exists() else None}
   put(out/'repeat-receipt.json',row);rows.append(row)
   if not passed:put(ROOT/'cycle02-pending-failure.json',row);raise RuntimeError('PENDING_REPEAT_FAILED')
 stable=all(sha(Path(p))==h for p,h in protected.items())
 if not stable:raise RuntimeError('CONTROL_CHANGED_DURING_VALIDATION')
 result={'schema':'OpenRemaster.PendingMilestoneValidation.v1','run_id':state['run_id'],'status':'PASS',
  'checks_per_pass':855,'checks_by_project':{p:c['tests'] for p,c in CONFIG.items()},'clean_repetitions':rows,
  'semantic_equivalence_excludes_only':'created_at_utc','all_owned_processes_exited':all(r['process_exited'] for r in rows),
  'source_hashes':baselines,'reviewed_control_epoch_unchanged':stable,'new_game_jobs':0,'runtime_fidelity_verified':False,
  'recorded_at_utc':now().isoformat(),'deadline_utc':state['deadline_utc']}
 put(ROOT/'cycle02-pending-validation.json',result)
 for project,c in CONFIG.items():
  lane=Path(state['output_ownership'][project]);put(lane/'PENDING_MILESTONE_SEALED.json',{'run_id':state['run_id'],'project':project,'status':'PASS',
    'report':c['report'],'initial_report_sha256':c['report_pin'],'clean_repeats':[r for r in rows if r['project']==project],
    'scope':'MECHANISM_NOT_RUNTIME_FIDELITY','coordinator_receipt_sha256':sha(ROOT/'cycle02-pending-validation.json')})
 print(json.dumps({'status':'PASS','checks_per_pass':855,'clean_repetitions_per_project':2,'per_project':result['checks_by_project'],'all_owned_processes_exited':True,'utc':result['recorded_at_utc'],'receipt_sha256':sha(ROOT/'cycle02-pending-validation.json')},indent=2))
if __name__=='__main__':main()
