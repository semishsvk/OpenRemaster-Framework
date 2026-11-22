"""Close carried-over C09 validation in the NEW authorized block.
Correct pins are supported by their original generation records and independent
13:49 status audit, not by substituting arbitrary current bytes after a failure.
The old failed harness, output files and original deadline remain untouched.
"""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'20261008-094028__AUTONOMOUS-4H-PREFLIGHT__lanes-ABC'
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
TASKS=[
 {'project':'OpenMDK1','id':'lookahead','script':'verify_default_chunk_lookahead.py','report':'default-chunk-lookahead-verification.json','tests':144,
  'pin':'6143ecf1f2f37dc8dd0691d74a3112b6da96ab11b8d445626e95251a9687891c','failed_pin':'679b10c9bfc37d7b2a596189b9b976f124a7a9249d278afcff8f2b7cf0de4c89','generation_utc':'2026-10-08T11:10:38.155620+00:00',
  'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py','observe_default_chunk_fpu.py','verify_default_chunk_lookahead.py'],'data':[],'ir':[]},
 {'project':'OpenUltima8','id':'contained-chain','script':'verify_contained_record_chain.py','report':'contained-record-chain-verification.json','tests':25,
  'pin':'361995cecd3a9a1b1287e049614f305a208790d431bf5fca66ca82968730c7e6','failed_pin':'361995cecd3a9a1b1287e049614f305a208790d431bf5fca66ca82968730c7e6','generation_utc':'2026-10-08T11:05:16.966726+00:00',
  'files':['ne_glob_candidates.py','verify_contained_record_chain.py'],'data':['map5-instance-ir.json'],'ir':[]},
 {'project':'OpenUltima8','id':'symbolic-overlay','script':'build_symbolic_parent_overlay.py','report':'symbolic-parentage-verification.json','tests':9,
  'pin':'e4ddd0d57189d73934d623a420dc9f3e5c3127c7eb1d79d394c9df300820f28a','failed_pin':'d6c0bc9ab344d583d610241529a731341025c2f316a1755b4ff9d1c0b739139c','generation_utc':'2026-10-08T11:13:34.041660+00:00',
  'files':['build_symbolic_parent_overlay.py'],'data':['map5-materialization-sourceir-v3.json','original-parent-gate-verification.json','record-population-verification.json','container-attachment-verification.json','contained-record-chain-verification.json'],'ir':['symbolic-parentage-overlay.json']}]
SOURCE_PINS={
 r'F:\Remaster Framework\source\MDK\MDK95.EXE':'e57bd63ba6af1ce201e3dd28a352e36ffa737267a9be0ed733fb81e6c40ba788',
 r'F:\Remaster Framework\source\Ultima 8\ENGLISH\U8.EXE':'1b1f470832e699a1eb4521f485acba8f1e62b641492a61de5c8d2561b01f3f6f',
 r'F:\Remaster Framework\source\Ultima 8\ENGLISH\STATIC\TYPEFLAG.DAT':'2b07f4a6acc5504d9d07c47d3686f74107cac7b594ccb18251e01249fadebc62'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,sort_keys=True);f.flush();os.fsync(f.fileno())
def sem(v):return {k:x for k,x in v.items() if k!='created_at_utc'}
def now():return datetime.now(timezone.utc)

def main():
 state=load(ROOT/'run-state.json');prior=load(OLD/'run-state.json')
 assert prior['status']=='CLOSED_DEADLINE_WITH_PENDING_VALIDATION'
 assert now()<datetime.fromisoformat(state['deadline_utc'])
 assert all(sha(Path(p))==h for p,h in dict(state['protected_inputs'],**SOURCE_PINS).items())
 harness=(OLD/'validate_cycle09.py').read_bytes();hsha=hashlib.sha256(harness).hexdigest()
 inputs={};review=[]
 for t in TASKS:
  old=Path(prior['output_ownership'][t['project']]);r=load(old/t['report'])
  assert sha(old/t['report'])==t['pin'] and r['status']=='PASS' and r['tests']==t['tests'] and r['created_at_utc']==t['generation_utc']
  assert t['failed_pin'].encode() in harness
  for n in t['files']:ast.parse((old/n).read_text(encoding='utf-8-sig'),filename=n)
  inputs[t['id']]={n:sha(old/n) for n in t['files']+t['data']+t['ir']+[t['report']]}
  review.append({'task':t['id'],'old_harness_expected':t['failed_pin'],'historically_observed_original':t['pin'],
    'original_output_bytes_unchanged':True,'generation_utc':t['generation_utc'],
    'independent_audit_utc':'2026-10-08T11:49:10.133846+00:00','pin_correction_needed':t['pin']!=t['failed_pin']})
 put(ROOT/'c09-pin-provenance-review.json',{'schema':'OpenRemaster.PinCorrectionReceipt.v1','status':'PASS_REVIEW',
  'old_harness_sha256':hsha,'historical_audit_sha256':'e0a1e70fdddc736ca5fb99213469a2c969582e063364917a99aa2205a3ce57fe',
  'basis':'Original generation SHA output in conversation and independent read-only status audit both precede this repeat request and agree on current original bytes.',
  'diagnosis':'Two unsupported expected digests in failed C09 harness; no matching alternate receipt evidenced. The exact cause of those wrong literals is not inferred.',
  'acceptance_changed':False,'new_reference_status':'Pinned reviewed originals; not rewritten or regenerated in place','review':review,'inputs':inputs})
 sys.path.insert(0,str(CP));from execution_journal import append_event
 rows=[]
 for repeat in ('clean-a','clean-b'):
  for t in TASKS:
   if (datetime.fromisoformat(state['deadline_utc'])-now()).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE')
   old=Path(prior['output_ownership'][t['project']]);out=Path(state['output_ownership'][t['project']])/'recovered-c09'/repeat/t['id'];out.mkdir(parents=True,exist_ok=False)
   for n in t['files']+t['data']:
    assert sha(old/n)==inputs[t['id']][n]
    with (out/n).open('xb') as f:f.write((old/n).read_bytes())
   start=now();clock=time.monotonic()
   p=subprocess.Popen([sys.executable,'-B',str(out/t['script'])],cwd=out,
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   append_event(ROOT/'execution-journal.jsonl',state['run_id'],'TEST_STARTED',task=t['id'],project=t['project'],repeat=repeat,pid=p.pid,output=str(out))
   try:stdout,stderr=p.communicate(timeout=30)
   except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=5);raise RuntimeError('OWN_BOUNDED_TEST_TIMEOUT')
   with (out/'execution.log').open('x',encoding='utf-8') as f:f.write(stdout+'\n'+stderr)
   got=load(out/t['report']) if (out/t['report']).is_file() else {}
   equal=sem(got)==sem(load(old/t['report']))
   unchanged=all(sha(out/n)==inputs[t['id']][n] and sha(old/n)==inputs[t['id']][n] for n in t['files']+t['data'])
   ir=all((out/n).is_file() and sha(out/n)==inputs[t['id']][n] for n in t['ir'])
   passed=p.returncode==0 and got.get('status')=='PASS' and got.get('tests')==t['tests'] and equal and unchanged and ir
   row={'project':t['project'],'task':t['id'],'repeat':repeat,'status':'PASS' if passed else 'FAIL','tests':t['tests'],
    'start_utc':start.isoformat(),'end_utc':now().isoformat(),'wall_seconds':time.monotonic()-clock,'pid':p.pid,'exit_code':p.returncode,'process_exited':p.poll() is not None,
    'semantic_report_equal':equal,'scripts_and_inputs_unchanged':unchanged,'ir_byte_identical':ir,'output_directory':str(out),
    'report_sha256':sha(out/t['report']) if (out/t['report']).is_file() else None}
   put(out/'repeat-receipt.json',row);rows.append(row)
   append_event(ROOT/'execution-journal.jsonl',state['run_id'],'TEST_FINISHED',task=t['id'],project=t['project'],pid=p.pid,status=row['status'],process_exited=row['process_exited'])
   if not passed:put(ROOT/'c09-recovery-failure.json',row);raise RuntimeError('CARRYOVER_VALIDATION_FAILED')
 assert sha(OLD/'validate_cycle09.py')==hsha and all(sha(Path(p))==h for p,h in dict(state['protected_inputs'],**SOURCE_PINS).items())
 result={'schema':'OpenRemaster.CarryoverValidation.v1','run_id':state['run_id'],'status':'PASS','previous_run_id':prior['run_id'],
  'previous_deadline_utc':prior['deadline_utc'],'validation_occurred_in':'NEW_R2_NOT_BACKDATED_TO_R1','checks_per_pass':178,
  'checks_by_project':{'OpenMDK1':144,'OpenUltima8':34,'OpenStonekeep':0},'clean_repetitions_per_task':2,'results':rows,
  'reconciliation_sha256':sha(ROOT/'c09-pin-provenance-review.json'),'semantic_equivalence_excludes_only':'created_at_utc',
  'old_evidence_and_failed_harness_unchanged':True,'old_completed_checks_remain':12364,'validated_carryover_checks':178,
  'combined_validated_scope_across_runs':12542,'new_game_jobs':0,'new_heavy_jobs':0,'all_owned_processes_exited':True,
  'fidelity_verified':False,'recorded_at_utc':now().isoformat()}
 put(ROOT/'carryover-c09-validation.json',result)
 for project in ('OpenMDK1','OpenUltima8'):
  put(Path(state['output_ownership'][project])/'C09_RECOVERY_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','run_id':state['run_id'],'project':project,'status':'PASS',
   'scope':'Validation of carried-over evidence, not new source mechanism','coordinator_receipt_sha256':sha(ROOT/'carryover-c09-validation.json'),
   'validated_cases_per_pass':result['checks_by_project'][project],'results':[r for r in rows if r['project']==project],
   'original_report_hashes':{t['report']:t['pin'] for t in TASKS if t['project']==project},'original_runtime_fidelity':False})
 print(json.dumps({k:v for k,v in result.items() if k!='results'},indent=2));print('RECEIPT_SHA256',sha(ROOT/'carryover-c09-validation.json'))
if __name__=='__main__':main()
