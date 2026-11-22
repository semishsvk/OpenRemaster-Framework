"""Fair finite clean-repeat validation of new source identity/parentage milestones.
No already-sealed numeric suite is rerun merely to correct its descriptive label.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,os,sys,time
ROOT=Path(__file__).resolve().parent
CFG={'OpenMDK1': {'files': ['static_probe.py', 'verify_f3_contract.py', 'verify_perspective_inputs.py', 'verify_perspective_span_inputs.py', 'verify_callback_identity.py', 'verify_default_short_pixels.py', 'verify_short_perspective_pixels.py', 'verify_profile_noninterchangeability.py'], 'data': [], 'tests': [('verify_profile_noninterchangeability.py', 'profile-noninterchangeability-verification.json', 43, '16afe320feb139454c0e2af583a9f68d31ab357ffa9a3a0307cb587737334e37')]}, 'OpenStonekeep': {'files': ['build_conditional_turn_contract.py'], 'data': ['callback-verification.json', 'wrapper-delta-verification.json', 'turn-admission-verification.json', 'turn-first-frame-verification.json', 'heading-actor-commit-verification.json'], 'tests': [('build_conditional_turn_contract.py', 'conditional-turn-contract-verification.json', 83, '38e0d5a256a9fc5e85425fa649ea9868e7ba7f044e6f856475893213e960e317')]}, 'OpenUltima8': {'files': ['ne_glob_candidates.py', 'verify_container_attachment.py'], 'data': ['ne_target_29_2adc.json', 'ne_target_29_2b36.json', 'map5-instance-ir.json'], 'tests': [('verify_container_attachment.py', 'container-attachment-verification.json', 116, 'af2652b98a0f264c03aa96fd55aab5342db25ba94a21953188c9337cb7892ce0')]}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,sort_keys=True)
def sem(v):return {k:x for k,x in v.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)
def main():
 s=load(ROOT/'run-state.json');deadline=datetime.fromisoformat(s['deadline_utc']);pins={};results=[]
 assert all(sha(Path(p))==h for p,h in s['resume_input_hashes'].items())
 for project,c in CFG.items():
  lane=Path(s['output_ownership'][project]);pins[project]={n:sha(lane/n) for n in c['files']+c['data']}
  for script,report,nt,pin in c['tests']:
   r=load(lane/report);assert sha(lane/report)==pin and r['status'] in ('PASS','PASS_CORRECTION') and r['tests']==nt
 put(ROOT/'cycle08-inputs.json',pins)
 for rep in ('cycle08-clean-a','cycle08-clean-b'):
  for project,c in CFG.items():
   if (deadline-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   lane=Path(s['output_ownership'][project]);out=lane/rep;out.mkdir(exist_ok=False)
   for n,h in pins[project].items():
    assert sha(lane/n)==h
    with (out/n).open('xb') as f:f.write((lane/n).read_bytes())
   tests=[]
   for script,report,nt,pin in c['tests']:
    start=now();clock=time.monotonic();p=subprocess.Popen([sys.executable,'-B',str(out/script)],cwd=out,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:so,se=p.communicate(timeout=30)
    except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=5);raise RuntimeError('OWN_TEST_TIMEOUT')
    with (out/(script+'.log')).open('x',encoding='utf-8') as f:f.write(so+'\n'+se)
    r=load(out/report) if (out/report).exists() else {};equal=sem(r)==sem(load(lane/report))
    ok=p.returncode==0 and r.get('status') in ('PASS','PASS_CORRECTION') and r.get('tests')==nt and equal
    tests.append({'script':script,'report':report,'status':'PASS' if ok else 'FAIL','tests':r.get('tests'),'pid':p.pid,'start_utc':start.isoformat(),'end_utc':now().isoformat(),'wall_seconds':time.monotonic()-clock,
     'exit_code':p.returncode,'process_exited':p.poll() is not None,'semantic_report_equal':equal,'report_sha256':sha(out/report) if (out/report).exists() else None})
    if not ok:put(ROOT/'cycle08-failure.json',tests[-1]);raise RuntimeError('CLEAN_REPEAT_FAILED')
   unchanged=all(sha(lane/n)==h and sha(out/n)==h for n,h in pins[project].items());assert unchanged
   if project=='OpenStonekeep':
    assert sha(out/'conditional-turn-contract.json')==sha(lane/'conditional-turn-contract.json')=='6831651d4bf36bffb607cf19a3be854faef25192086012e4cd9232387bf76cc2'
   row={'project':project,'repeat':rep,'status':'PASS','tests':tests,'scripts_and_inputs_unchanged':True};put(out/'repeat-receipt.json',row);results.append(row)
 assert all(sha(Path(p))==h for p,h in s['resume_input_hashes'].items())
 receipt={'schema':'OpenRemaster.FairCycleValidation.v3','run_id':s['run_id'],'cycle':8,'status':'PASS','mode':'INTERLEAVED','checks_per_pass':242,
  'per_project':{p:sum(t[2] for t in c['tests']) for p,c in CFG.items()},'results':results,'clean_repetitions_per_lane':2,'source_hashes':pins,
  'semantic_equivalence_excludes_only':'created_at_utc','all_owned_processes_exited':True,'new_game_jobs':0,'new_heavy_jobs':0,'runtime_fidelity_verified':False,'deadline_utc':s['deadline_utc'],'recorded_at_utc':now().isoformat()}
 put(ROOT/'cycle08-validation.json',receipt)
 for project,c in CFG.items():
  lane=Path(s['output_ownership'][project]);put(lane/'CYCLE08_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','run_id':s['run_id'],'checkpoint':s['run_id']+'-'+project+'-C08','project':project,'status':'PASS',
   'checks_per_pass':receipt['per_project'][project],'initial_report_hashes':{t[1]:t[3] for t in c['tests']},'source_hashes':pins[project],'clean_repetitions':[r for r in results if r['project']==project],
   'scope':'ORIGINAL_CODE_MECHANISM_OR_CORRECTED_SCOPE_NOT_FULL_RUNTIME','coordinator_receipt_sha256':sha(ROOT/'cycle08-validation.json')})
 print(json.dumps({'status':'PASS','checks_per_pass':242,'per_project':receipt['per_project'],'clean_repetitions_per_lane':2,'utc':receipt['recorded_at_utc'],'sha256':sha(ROOT/'cycle08-validation.json')},indent=2))
if __name__=='__main__':main()
