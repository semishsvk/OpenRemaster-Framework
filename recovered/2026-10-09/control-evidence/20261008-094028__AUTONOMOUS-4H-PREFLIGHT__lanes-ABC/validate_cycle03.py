"""Two clean repetitions of the next three newly completed lane mechanisms.
Finite sequential harness, not a new dispatcher or background worker.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
CFG={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py'],'data':[],
  'script':'verify_perspective_span_inputs.py','report':'perspective-span-input-verification.json','tests':109,'pin':'6cd30044ff00bd631a1f46b19a72664e4031f849b397d9ff4fb7f6b164d94955'},
 'OpenStonekeep':{'files':['source_manifest.py','le_fixups.py','verify_turn_intent.py','verify_ordinary_turn_envelope.py'],'data':[],
  'script':'verify_ordinary_turn_envelope.py','report':'ordinary-turn-envelope-verification.json','tests':480,'pin':'7c74f837dbe7fc5ee6b6d4f3b071ceef89419e32d10e9ac2d58d279de7e14ede'},
 'OpenUltima8':{'files':['ne_glob_candidates.py','verify_glob_request_gate_v2.py'],'data':['activation-helper-resolution.json','glob-entry-callers.json','materialization-receipt.json'],
  'script':'verify_glob_request_gate_v2.py','report':'glob-request-gate-verification-v2.json','tests':1562,'pin':'2a3017d8998e40ddbcefcfd8438fab12d42015c7b3084c776a7112fb500e23a3'}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,sort_keys=True)
def sem(d):return {k:v for k,v in d.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)
def main():
 state=load(ROOT/'run-state.json');deadline=datetime.fromisoformat(state['deadline_utc']);rows=[];pins={}
 if any(sha(Path(p))!=h for p,h in state['resume_input_hashes'].items()):raise RuntimeError('CONTROL_EPOCH_DRIFT')
 for name,c in CFG.items():
  lane=Path(state['output_ownership'][name]);r=load(lane/c['report'])
  assert sha(lane/c['report'])==c['pin'] and r['status']=='PASS' and r['tests']==c['tests']
  pins[name]={f:sha(lane/f) for f in c['files']+c['data']+[c['report']]}
 put(ROOT/'cycle03-inputs.json',pins)
 for rep in ('cycle03-clean-a','cycle03-clean-b'):
  for project,c in CFG.items():
   if (deadline-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   lane=Path(state['output_ownership'][project]);out=lane/rep;out.mkdir(exist_ok=False)
   for n in c['files']+c['data']:
    assert sha(lane/n)==pins[project][n]
    with (out/n).open('xb') as f:f.write((lane/n).read_bytes())
   start=now();clock=time.monotonic();p=subprocess.Popen([sys.executable,'-B',str(out/c['script'])],cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:stdout,stderr=p.communicate(timeout=30)
   except subprocess.TimeoutExpired:
    p.kill();p.communicate(timeout=5);raise RuntimeError('OWN_TEST_TIMEOUT')
   with (out/'test.log').open('x',encoding='utf-8') as f:f.write(stdout+'\n'+stderr)
   d=load(out/c['report']) if (out/c['report']).is_file() else {};equal=sem(d)==sem(load(lane/c['report']))
   unchanged=all(sha(out/n)==pins[project][n] and sha(lane/n)==pins[project][n] for n in c['files']+c['data'])
   ok=p.returncode==0 and d.get('status')=='PASS' and d.get('tests')==c['tests'] and equal and unchanged
   row={'project':project,'repeat':rep,'status':'PASS' if ok else 'FAIL','tests':d.get('tests'),'pid':p.pid,'start_utc':start.isoformat(),'end_utc':now().isoformat(),'wall_seconds':time.monotonic()-clock,
    'exit_code':p.returncode,'process_exited':p.poll() is not None,'semantic_report_equal':equal,'scripts_and_inputs_unchanged':unchanged,'report_sha256':sha(out/c['report']) if (out/c['report']).exists() else None}
   put(out/'repeat-receipt.json',row);rows.append(row)
   if not ok:put(ROOT/'cycle03-failure.json',row);raise RuntimeError('CLEAN_REPEAT_FAILED')
 assert all(sha(Path(p))==h for p,h in state['resume_input_hashes'].items())
 result={'schema':'OpenRemaster.FairCycleValidation.v2','run_id':state['run_id'],'cycle':3,'status':'PASS','mode':'INTERLEAVED','deadline_utc':state['deadline_utc'],
  'checks_per_pass':2151,'checks_by_project':{p:c['tests'] for p,c in CFG.items()},'clean_repetitions_per_lane':2,'results':rows,'source_hashes':pins,
  'semantic_equivalence_excludes_only':'created_at_utc','all_owned_processes_exited':all(r['process_exited'] for r in rows),'new_heavy_jobs':0,'new_game_jobs':0,'runtime_fidelity_verified':False,'recorded_at_utc':now().isoformat()}
 put(ROOT/'cycle03-validation.json',result)
 for project,c in CFG.items():
  lane=Path(state['output_ownership'][project]);put(lane/'CYCLE03_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','run_id':state['run_id'],'checkpoint':state['run_id']+'-'+project+'-C03','project':project,
    'status':'PASS','checks_per_pass':c['tests'],'report':c['report'],'initial_report_sha256':c['pin'],'source_hashes':pins[project],'clean_repetitions':[r for r in rows if r['project']==project],
    'scope':'ORIGINAL_SOURCE_MECHANISM_NOT_FULL_RUNTIME','runtime_fidelity_verified':False,'coordinator_receipt_sha256':sha(ROOT/'cycle03-validation.json')})
 print(json.dumps({'status':'PASS','checks_per_pass':2151,'checks_by_lane':result['checks_by_project'],'clean_repetitions_per_lane':2,'all_owned_processes_exited':True,'utc':result['recorded_at_utc'],'receipt_sha256':sha(ROOT/'cycle03-validation.json')},indent=2))
if __name__=='__main__':main()
