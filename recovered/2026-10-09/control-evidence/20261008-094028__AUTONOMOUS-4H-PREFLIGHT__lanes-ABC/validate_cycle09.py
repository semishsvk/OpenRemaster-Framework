"""Clean repeats for the remaining completed proofs, with per-task isolation.
A composition test reads the original pinned receipt, not a timestamp-changed
receipt produced by its neighbor. No old evidence is overwritten to force a match.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,sys,subprocess,time
ROOT=Path(__file__).resolve().parent
TASKS=[
 {'project':'OpenMDK1','id':'lookahead','script':'verify_default_chunk_lookahead.py','report':'default-chunk-lookahead-verification.json','tests':144,'pin':'679b10c9bfc37d7b2a596189b9b976f124a7a9249d278afcff8f2b7cf0de4c89',
 'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py','observe_default_chunk_fpu.py','verify_default_chunk_lookahead.py'],'data':[],'ir':[]},
 {'project':'OpenUltima8','id':'contained-chain','script':'verify_contained_record_chain.py','report':'contained-record-chain-verification.json','tests':25,'pin':'361995cecd3a9a1b1287e049614f305a208790d431bf5fca66ca82968730c7e6',
 'files':['ne_glob_candidates.py','verify_contained_record_chain.py'],'data':['map5-instance-ir.json'],'ir':[]},
 {'project':'OpenUltima8','id':'symbolic-overlay','script':'build_symbolic_parent_overlay.py','report':'symbolic-parentage-verification.json','tests':9,'pin':'d6c0bc9ab344d583d610241529a731341025c2f316a1755b4ff9d1c0b739139c',
 'files':['build_symbolic_parent_overlay.py'],'data':['map5-materialization-sourceir-v3.json','original-parent-gate-verification.json','record-population-verification.json','container-attachment-verification.json','contained-record-chain-verification.json'],
 'ir':['symbolic-parentage-overlay.json']}]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,sort_keys=True)
def sem(x):return {k:v for k,v in x.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)
def main():
 s=load(ROOT/'run-state.json');end=datetime.fromisoformat(s['deadline_utc']);inputs={};rows=[]
 assert all(sha(Path(p))==h for p,h in s['resume_input_hashes'].items())
 for t in TASKS:
  lane=Path(s['output_ownership'][t['project']]);r=load(lane/t['report']);assert sha(lane/t['report'])==t['pin'] and r['status']=='PASS' and r['tests']==t['tests']
  inputs[t['id']]={n:sha(lane/n) for n in t['files']+t['data']+t['ir']}
 put(ROOT/'cycle09-inputs.json',inputs)
 for rep in ('cycle09-clean-a','cycle09-clean-b'):
  for t in TASKS:
   if (end-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   lane=Path(s['output_ownership'][t['project']]);parent=lane/rep;parent.mkdir(exist_ok=True);out=parent/t['id'];out.mkdir(exist_ok=False)
   for n in t['files']+t['data']:
    assert sha(lane/n)==inputs[t['id']][n]
    with (out/n).open('xb') as f:f.write((lane/n).read_bytes())
   start=now();clock=time.monotonic();p=subprocess.Popen([sys.executable,'-B',str(out/t['script'])],cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:stdout,stderr=p.communicate(timeout=30)
   except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=5);raise RuntimeError('OWN_TEST_TIMEOUT')
   with (out/'test.log').open('x',encoding='utf-8') as f:f.write(stdout+'\n'+stderr)
   got=load(out/t['report']) if (out/t['report']).exists() else {};equal=sem(got)==sem(load(lane/t['report']));ir_ok=all((out/n).exists() and sha(out/n)==inputs[t['id']][n] for n in t['ir'])
   stable=all(sha(out/n)==h and sha(lane/n)==h for n,h in inputs[t['id']].items() if n not in t['ir'])
   ok=p.returncode==0 and got.get('status')=='PASS' and got.get('tests')==t['tests'] and equal and ir_ok and stable
   row={'project':t['project'],'task':t['id'],'repeat':rep,'status':'PASS' if ok else 'FAIL','pid':p.pid,'start_utc':start.isoformat(),'end_utc':now().isoformat(),'wall_seconds':time.monotonic()-clock,
    'exit_code':p.returncode,'process_exited':p.poll() is not None,'tests':got.get('tests'),'semantic_report_equal':equal,'ir_byte_identical':ir_ok,'scripts_and_inputs_unchanged':stable,'report_sha256':sha(out/t['report']) if (out/t['report']).exists() else None}
   put(out/'repeat-receipt.json',row);rows.append(row)
   if not ok:put(ROOT/'cycle09-failure.json',row);raise RuntimeError('CLEAN_REPEAT_FAILED')
 assert all(sha(Path(p))==h for p,h in s['resume_input_hashes'].items())
 result={'schema':'OpenRemaster.FairCycleValidation.v3','run_id':s['run_id'],'cycle':9,'status':'PASS','checks_per_pass':178,'mode':'INTERLEAVED','results':rows,'source_hashes':inputs,
  'clean_repetitions_per_task':2,'semantic_equivalence_excludes_only':'created_at_utc','all_owned_processes_exited':True,'new_heavy_jobs':0,'new_game_jobs':0,
  'Stonekeep_state':'Completed conditional-state contract remains sealed; next frame/event-body obligations are not replaced with repeated old tests.',
  'recorded_at_utc':now().isoformat(),'deadline_utc':s['deadline_utc']}
 put(ROOT/'cycle09-validation.json',result)
 for project in ('OpenMDK1','OpenUltima8'):
  lane=Path(s['output_ownership'][project]);put(lane/'CYCLE09_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','project':project,'run_id':s['run_id'],'checkpoint':s['run_id']+'-'+project+'-C09','status':'PASS',
   'tests_per_pass':sum(t['tests'] for t in TASKS if t['project']==project),'initial_reports':{t['report']:t['pin'] for t in TASKS if t['project']==project},'clean_repetitions':[r for r in rows if r['project']==project],
   'scope':'BOUNDED_MECHANISM_OR_SYMBOLIC_COMPOSITION_NOT_FULL_RUNTIME','coordinator_receipt_sha256':sha(ROOT/'cycle09-validation.json')})
 print(json.dumps({'status':'PASS','checks_per_pass':178,'per_lane':{'OpenMDK1':144,'OpenUltima8':34,'OpenStonekeep':0},'clean_repeats_per_task':2,'utc':result['recorded_at_utc'],'sha256':sha(ROOT/'cycle09-validation.json')},indent=2))
if __name__=='__main__':main()
