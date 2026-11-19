"""Resume the existing finite block, without resetting its deadline or approving native dispatch.
Only this block's reports/state are written. Production/config files and live jobs are read-only.
"""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,sort_keys=True)
def main():
 p=ROOT/'run-state.json';before=p.read_bytes();s=json.loads(before);now=datetime.now(timezone.utc)
 assert s['run_id']=='AUTONOMOUS4H-20261008T073923Z-ABC'
 assert s['deadline_utc']=='2026-10-08T11:39:23.845443+00:00'
 if (datetime.fromisoformat(s['deadline_utc'])-now).total_seconds()<300:raise RuntimeError('SHUTDOWN_RESERVE_OR_DEADLINE')
 observed={name:sha(Path(name)) for name in s['protected_inputs']}
 changed=[{'path':p,'before_sha256':h,'observed_sha256':observed[p]} for p,h in s['protected_inputs'].items() if h!=observed[p]]
 expected_changes={'orch_k003.py':'1f07decfc9d40833a1723b34e986edb79ec1a9a2d51a55919fe2684285e962b2','worker-commissioning.json':'d183b3edfbdb528ef7989e71f36203637dd9b6febb5fef1709e626e42dafd81d'}
 if {Path(d['path']).name:d['observed_sha256'] for d in changed}!=expected_changes:raise RuntimeError('UNREVIEWED_CONTROL_DELTA')
 for lane in s['lanes'].values():
  directory=Path(lane['output'])
  for name,record in lane['completed_reports'].items():
   if sha(directory/name)!=record['sha256']:raise RuntimeError('CHECKPOINT_ARTIFACT_DRIFT:'+name)
 assert sha(ROOT/'cycle01-validation-receipt.json')==s['completed_cycle01_validation']['sha256']
 code=(CP/'orch_k003.py').read_text();ast.parse(code)
 audit={'schema':'OpenRemaster.ResumeControlReview.v1','scope':'READ_ONLY_DEPENDENCY_REVIEW_NOT_PRODUCTION_CERTIFICATION',
  'run_id':s['run_id'],'reviewed_at_utc':now.isoformat(),'deadline_utc':s['deadline_utc'],'changes':changed,
  'observations':['NativeLocalQueue has route preference in route().',
    'executable_runtime still invokes subprocess.run directly; selected worker identity is not passed into this branch.',
    'godot_runtime invokes godot-runtime-worker/run_job.py; no NativeLocalQueue submission is visible in these inspected files.',
    'The inspected lease is still job-local out/worker-lease.json; additional external exclusivity not established here.'],
  'worker_registry_claim':load(CP/'worker-commissioning.json')['workers']['HomePC-NativeWorker'],
  'native_dispatch_allowed_by_this_review':False,'decision':'CONTINUE_BOUND_READ_ONLY_EVIDENCE_ONLY',
  'parallel_mode':'INTERLEAVED','reason':'No exposed subagents and no verified free global heavy capacity; existing processes remain untouched.',
  'owned_process_observation':'No existing process matched this run paths in preflight; audit terminal excluded.',
  'budget_note':'Prior interruption is not execution time. Original wall-clock deadline retained.',
  'input_epoch_hashes':observed,'new_heavy_jobs':0,'new_game_jobs':0,'azrael_polling':False}
 put(ROOT/'resume-0920-control-review.json',audit)
 archive=ROOT/'run-state-before-resume-0920.json'
 with archive.open('xb') as f:f.write(before)
 s['protected_input_epochs']=s.get('protected_input_epochs',[])+[{'epoch':'resume-0920','observed_utc':now.isoformat(),'input_sha256':observed,'review_sha256':sha(ROOT/'resume-0920-control-review.json'),'authority':'READ_ONLY_EVIDENCE_CONTINUATION_ONLY'}]
 s['resumed_at_utc']=now.isoformat();s['status']='ACTIVE_INTERLEAVED_SESSION';s['observed_at_utc']=now.isoformat()
 s['resume_input_hashes']=observed;s['native_worker_gate_observed']=audit['worker_registry_claim']
 s['native_dispatch_gate']='NOT_ESTABLISHED_BY_REGISTRY_FLAG_ALONE'
 s['continuation_gaps']=s.get('continuation_gaps',[])+[{'last_new_result_utc':'2026-10-08T08:42:45.838235+00:00','resumed_at_utc':now.isoformat(),'execution_in_gap':'NOT_CLAIMED'}]
 s['next_action']='Clean-repeat the new MDK gradient and original U8 GLOB results; advance Stonekeep continuation; then cycle fairly.'
 lock=ROOT/'.state-writer-lock';lock.mkdir(exist_ok=False)
 try:
  if p.read_bytes()!=before:raise RuntimeError('STATE_COMPARE_AND_SWAP_FAILED')
  temp=ROOT/'run-state.resumed.tmp'
  with temp.open('x',encoding='utf-8') as f:json.dump(s,f,indent=2,sort_keys=True);f.flush();os.fsync(f.fileno())
  os.replace(temp,p)
 finally:lock.rmdir()
 sys.path.insert(0,str(CP));from execution_journal import append_event
 append_event(ROOT/'execution-journal.jsonl',s['run_id'],'SESSION_RESUMED',mode='INTERLEAVED',deadline_utc=s['deadline_utc'],control_review_sha256=sha(ROOT/'resume-0920-control-review.json'))
 print(json.dumps({'run_id':s['run_id'],'resumed_at_utc':now.isoformat(),'deadline_utc':s['deadline_utc'],'mode':'INTERLEAVED','control_review':'READ_ONLY_CONTINUATION_ALLOWED','native_dispatch':'NOT_PROMOTED','review_sha256':sha(ROOT/'resume-0920-control-review.json')},indent=2))
if __name__=='__main__':main()
