"""Start an explicitly user-requested second block and terminally reconcile R1.
No dispatch, lease takeover, production modification or corpus/worktree writes.
Only the new output tree and a compare-and-swap closure of our old run state.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'20261008-094028__AUTONOMOUS-4H-PREFLIGHT__lanes-ABC'
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
START=datetime.fromisoformat('2026-10-08T11:56:09.638356+00:00')
RUN='AUTONOMOUS4H-R2-20261008T115609Z-ABC'
PROJECTS=['OpenMDK1','OpenStonekeep','OpenUltima8']
OUT={p:rf'F:\Remaster Framework\output\projects\{p}\evidence\20261008-135657__AUTONOMOUS-4H-R2__cycle01' for p in PROJECTS}

def sha(b):return hashlib.sha256(b).hexdigest()
def packed(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode('utf-8')
def put(p,v):
 with p.open('xb') as f:f.write(v if isinstance(v,bytes) else packed(v));f.flush();os.fsync(f.fileno())
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
 now=datetime.now(timezone.utc);assert START<=now<START+timedelta(hours=4)
 oldraw=(OLD/'run-state.json').read_bytes();prior=json.loads(oldraw)
 assert prior['run_id']=='AUTONOMOUS4H-20261008T073923Z-ABC'
 assert datetime.fromisoformat(prior['deadline_utc'])<now and prior['live_leases_acquired']==[]
 ps='Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Depth 3'
 result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',ps],capture_output=True,text=True,timeout=15)
 if result.returncode:raise RuntimeError('PROCESS_CENSUS_UNAVAILABLE')
 processes=json.loads(result.stdout);byid={int(p['ProcessId']):p for p in processes}
 excluded={os.getpid()};parent=os.getpid()
 while parent in byid:
  parent=int(byid[parent]['ParentProcessId'])
  if parent in excluded or parent==0:break
  excluded.add(parent)
 markers=[str(OLD).lower()]+[str(p).lower() for p in prior['output_ownership'].values()]+[prior['run_id'].lower()]
 relevant={int(p['ProcessId']) for p in processes if int(p['ProcessId']) not in excluded and any(m in str(p.get('CommandLine') or '').lower() for m in markers)}
 while True:
  child={int(p['ProcessId']) for p in processes if int(p['ParentProcessId']) in relevant and int(p['ProcessId']) not in excluded}
  if child<=relevant:break
  relevant|=child
 observed=[{k:byid[pid].get(k) for k in ['ProcessId','ParentProcessId','Name','CreationDate']} for pid in sorted(relevant)]
 put(ROOT/'predecessor-run-state-original.json',oldraw)
 put(ROOT/'predecessor-process-snapshot.json',{'at_utc':now.isoformat(),'run_id':prior['run_id'],'matching_processes':observed,'scope':'Command-line run paths and descendants, current inspection and ancestors excluded','no_processes_terminated':True})
 closed=False
 if not relevant:
  lock=OLD/'.terminal-state-cas.lock';lock.mkdir(exist_ok=False)
  try:
   if (OLD/'run-state.json').read_bytes()!=oldraw:raise RuntimeError('OLD_STATE_CHANGED')
   terminal=dict(prior,status='CLOSED_DEADLINE_WITH_PENDING_VALIDATION',observed_at_utc=now.isoformat(),
    terminalized_at_utc=now.isoformat(),terminal_reason='Expired original deadline; no matching run process. C09 was NOT completed within R1.',
    validated_cases_at_close=12364,pending_cases_at_close=178,repeated_new_run_id=RUN,
    closure_note='New R2 may validate carried-over work; never backdate that validation into R1.',
    previous_active_state_sha256=sha(oldraw),process_snapshot_reference=str(ROOT/'predecessor-process-snapshot.json'))
   put(OLD/'R1_TERMINAL_CHECKPOINT.json',terminal)
   tmp=OLD/'run-state.terminal.tmp';put(tmp,terminal)
   if (OLD/'run-state.json').read_bytes()!=oldraw:raise RuntimeError('OLD_STATE_CONCURRENT_WRITER')
   os.replace(tmp,OLD/'run-state.json');closed=True
  finally:lock.rmdir()
 elif relevant:raise RuntimeError('PREDECESSOR_RUN_PROCESS_UNRECONCILED')
 protected={str(CP/n):sha((CP/n).read_bytes()) for n in ['portfolio-lanes-20261008-v3.json','capabilities.json','worker-commissioning.json','orch_k003.py','leases.py','execution_journal.py']}
 portfolio=load(CP/'portfolio-lanes-20261008-v3.json');assert portfolio['policy']['temporary_focus_lane_ids']==PROJECTS
 state={'schema':'OpenRemaster.AutonomousBlockState.v1','run_id':RUN,'user_authority':'Explicit request: Opakuj beh',
  'started_at_utc':START.isoformat(),'deadline_utc':(START+timedelta(hours=4)).isoformat(),'observed_at_utc':now.isoformat(),
  'status':'ACTIVE_INTERLEAVED_SESSION','mode':'INTERLEAVED','requested_duration_hours':4,
  'max_lane_workers':3,'max_heavy_global':3,'wip_per_project':1,'checkpoint_interval_seconds':900,'shutdown_reserve_seconds':300,
  'max_repairs_without_new_evidence':2,'protected_inputs':protected,'output_ownership':OUT,
  'scope':'Bounded read-only corpus/evidence review and small isolated mechanism tests in own new output trees.',
  'native_execution_admission':'BLOCKED_UNVERIFIED_GLOBAL_SLOTS_AND_EXECUTABLE_RUNTIME_ADAPTER_BINDING',
  'admission_evidence':'Registry marks native routable but canonical executable_runtime branch directly subprocesses under caller; do not equate worker selection metadata with execution identity.',
  'subagents_exposed':False,'model_router_exposed':False,'codex_on_path':False,
  'new_heavy_jobs':0,'new_native_game_jobs':0,'new_gpu_jobs':0,'live_leases_acquired':[],
  'predecessor':{'run_id':prior['run_id'],'deadline_utc':prior['deadline_utc'],'terminalized':closed,'validated_at_close':12364,'pending_at_close':178},
  'lanes':{p:{'state':'PREFLIGHT','active_owned_pid':None,'new_checks':0,'output':OUT[p]} for p in PROJECTS},
  'scope_exclusions':['Azrael Retail paused','Demo closed','No game-worktree writes','No ACL/account/service changes','No live-lease changes'],
  'next_action':'Resolve C09 pin provenance and execute isolated clean repeats under new R2; then one next bounded task per focus lane.'}
 put(ROOT/'run-state.json',state)
 sys.path.insert(0,str(CP));from execution_journal import append_event
 append_event(ROOT/'execution-journal.jsonl',RUN,'NEW_RUN_PREFLIGHT',deadline_utc=state['deadline_utc'],mode='INTERLEAVED',predecessor_terminalized=closed)
 if closed:append_event(OLD/'execution-journal.jsonl',prior['run_id'],'RUN_TERMINALIZED_AFTER_DEADLINE',state='CLOSED_DEADLINE_WITH_PENDING_VALIDATION',pending_cases=178,new_validation_run_id=RUN)
 for p,out in OUT.items():put(Path(out)/'run-link.json',{'run_id':RUN,'coordinator':str(ROOT),'deadline_utc':state['deadline_utc'],'owner_scope':'This new evidence output only','game_worktree_mutation':False})
 print(json.dumps({'run_id':RUN,'start_utc':state['started_at_utc'],'deadline_utc':state['deadline_utc'],'mode':'INTERLEAVED','predecessor_terminalized':closed,'old_pending_cases':178,'new_heavy_jobs':0,'run_state_sha256':sha((ROOT/'run-state.json').read_bytes())},indent=2))
if __name__=='__main__':main()
