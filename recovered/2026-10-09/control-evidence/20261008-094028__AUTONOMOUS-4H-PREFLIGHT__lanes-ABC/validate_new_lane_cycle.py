"""Seal only the new all-lane proofs in two independent clean copies.
The run/deadline is unchanged; this finite harness is not a background worker.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
CFG={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_signed_width_path.py'],
  'data':[],'script':'verify_signed_width_path.py','report':'signed-width-verification.json','tests':189,
  'pin':'88c6fdf510fd6f8091ca19bec396bbc2fc9ec9d69d99d224b965b2f51ea90781','ir':[]},
 'OpenStonekeep':{'files':['source_manifest.py','le_fixups.py','verify_turn_intent.py'],
  'data':[],'script':'verify_turn_intent.py','report':'turn-intent-verification.json','tests':72,
  'pin':'92b333805a003c916d42b0d44bc7003684d72676813374af415470f1220a0456','ir':[]},
 'OpenUltima8':{'files':['build_verified_map5_ir_v3b.py'],
  'data':['materialization-receipt.json','original-glob-verification.json','original-glob-positions.json','map5-instance-ir.json'],
  'script':'build_verified_map5_ir_v3b.py','report':'materialization-v3b-verification.json','tests':11,
  'pin':None,'ir':['map5-materialization-sourceir-v3.json']}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,d):
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,sort_keys=True)
def sem(x):return {k:v for k,v in x.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)
def main():
 s=load(ROOT/'run-state.json');end=datetime.fromisoformat(s['deadline_utc']);base={};rows=[]
 if any(sha(Path(p))!=h for p,h in s['resume_input_hashes'].items()):raise RuntimeError('UNREVIEWED_CONTROL_DRIFT')
 for project,c in CFG.items():
  p=Path(s['output_ownership'][project]);r=load(p/c['report'])
  if r['status']!='PASS' or r['tests']!=c['tests'] or (c['pin'] and sha(p/c['report'])!=c['pin']):raise RuntimeError('INITIAL_RESULT_DRIFT')
  if project=='OpenUltima8' and r['sourceir_sha256']!='a5c8c9aa9e9da9ceecd41c1cecd18e7f20c18f2822ba38b878b07f613b8a5638':raise RuntimeError('CORRECTED_IR_DRIFT')
  base[project]={n:sha(p/n) for n in c['files']+c['data']+c['ir']+[c['report']]}
 put(ROOT/'cycle02b-inputs.json',base)
 for rep in ['cycle02b-clean-a','cycle02b-clean-b']:
  for project,c in CFG.items():
   if (end-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   lane=Path(s['output_ownership'][project]);out=lane/rep;out.mkdir(exist_ok=False)
   for n in c['files']+c['data']:
    if sha(lane/n)!=base[project][n]:raise RuntimeError('COPY_INPUT_CHANGED')
    with (out/n).open('xb') as f:f.write((lane/n).read_bytes())
   started=now();clock=time.monotonic()
   p=subprocess.Popen([sys.executable,'-B',str(out/c['script'])],cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:stdout,stderr=p.communicate(timeout=30)
   except subprocess.TimeoutExpired:
    p.kill();p.communicate(timeout=5);raise RuntimeError('OWN_BOUNDED_TEST_TIMEOUT')
   with (out/'test.log').open('x',encoding='utf-8') as f:f.write(stdout+'\n'+stderr)
   got=load(out/c['report']) if (out/c['report']).is_file() else {}
   equal=sem(got)==sem(load(lane/c['report']));irs=all((out/n).exists() and sha(out/n)==base[project][n] for n in c['ir'])
   same=all(sha(out/n)==base[project][n] and sha(lane/n)==base[project][n] for n in c['files']+c['data'])
   ok=p.returncode==0 and got.get('status')=='PASS' and got.get('tests')==c['tests'] and equal and irs and same
   row={'project':project,'repeat':rep,'status':'PASS' if ok else 'FAIL','pid':p.pid,'started_at_utc':started.isoformat(),'finished_at_utc':now().isoformat(),
    'duration_seconds':time.monotonic()-clock,'exit_code':p.returncode,'process_exited':p.poll() is not None,'tests':got.get('tests'),'semantic_report_equal':equal,'ir_byte_identical':irs,'scripts_and_inputs_unchanged':same,'report_sha256':sha(out/c['report']) if (out/c['report']).exists() else None}
   put(out/'repeat-receipt.json',row);rows.append(row)
   if not ok:put(ROOT/'cycle02b-failure.json',row);raise RuntimeError('CLEAN_REPEAT_FAILED')
 if any(sha(Path(p))!=h for p,h in s['resume_input_hashes'].items()):raise RuntimeError('CONTROL_CHANGED_DURING_REPEATS')
 result={'schema':'OpenRemaster.FairCycleValidation.v2','run_id':s['run_id'],'cycle':'02b','status':'PASS','mode':'INTERLEAVED','deadline_utc':s['deadline_utc'],
  'checks_per_pass':272,'clean_repetitions_per_lane':2,'source_hashes':base,'results':rows,'new_heavy_jobs':0,'new_game_jobs':0,'fidelity_verified':False,
  'all_owned_processes_exited':all(r['process_exited'] for r in rows),'semantic_equivalence_excludes_only':'created_at_utc','recorded_at_utc':now().isoformat()}
 put(ROOT/'cycle02b-validation.json',result)
 for project,c in CFG.items():
  lane=Path(s['output_ownership'][project]);put(lane/'CYCLE02B_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','project':project,'run_id':s['run_id'],
    'checkpoint':s['run_id']+'-'+project+'-C02B','status':'PASS','report':c['report'],'report_sha256':base[project][c['report']],
    'checks_per_pass':c['tests'],'initial_pass':True,'clean_repetitions':[r for r in rows if r['project']==project],'source_hashes':base[project],
    'scope':'SOURCE_MECHANISM_AND_EVIDENCE_IR_NOT_RUNTIME','deadline_utc':s['deadline_utc'],'coordinator_receipt_sha256':sha(ROOT/'cycle02b-validation.json')})
 print(json.dumps({'status':'PASS','checks_per_pass':272,'checks_by_lane':{p:c['tests'] for p,c in CFG.items()},'clean_repeats_per_lane':2,'all_owned_processes_exited':True,'utc':result['recorded_at_utc'],'receipt_sha256':sha(ROOT/'cycle02b-validation.json')},indent=2))
if __name__=='__main__':main()
