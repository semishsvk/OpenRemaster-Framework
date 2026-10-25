"""Read-only audit / terminal sealing for this fixed-deadline R2 block.
Does not repair evidence, run tests, stop arbitrary processes or change resources.
--audit-only has no writes. A terminal reason is explicit and cannot restart time.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def packed(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
def put(p,v):
 with p.open('xb') as f:f.write(v if isinstance(v,bytes) else packed(v));f.flush();os.fsync(f.fileno())
def sem(v):return {k:x for k,x in v.items() if k!='created_at_utc'}

def audit(state):
 problems=[];cycles=[];counts={p:0 for p in state['output_ownership']};checked=0
 for path in sorted(ROOT.glob('phase*-validation.json')):
  receipt=load(path);cycle_counts={};rows=receipt.get('results',[])
  if receipt.get('status')!='PASS':problems.append(str(path)+':NOT_PASS');continue
  for row in rows:
   try:
    lane=Path(state['output_ownership'][row['project']]);out=Path(row['output_directory'])
    if not out.resolve().is_relative_to(lane.resolve()):raise ValueError('RESULT_PATH_ESCAPE')
    matches=[f for f in out.glob('*.json') if sha(f)==row['report_sha256']]
    if len(matches)!=1:raise ValueError('REPEAT_REPORT_MISSING_OR_AMBIGUOUS')
    rpt=matches[0];initial=lane/rpt.name;task=receipt['inputs'][row['task']]
    if sha(initial)!=task['initial_report_sha256']:raise ValueError('INITIAL_REPORT_PIN')
    rr=load(rpt);ir=load(initial)
    if sem(rr)!=sem(ir) or row['exit_code']!=0 or not row['process_exited'] or row['status']!='PASS':raise ValueError('REPEAT_SEMANTICS_OR_EXIT')
    if type(rr.get('tests')) is not int or rr['tests']!=row['tests']:raise ValueError('CASE_COUNT')
    for filename,h in task['script_hashes'].items():
     if sha(lane/filename)!=h or sha(out/filename)!=h:raise ValueError('SOFTWARE_DRIFT:'+filename)
    checked+=1;cycle_counts.setdefault(row['project'],{}).setdefault(row['task'],[]).append(row)
   except Exception as e:problems.append(str(path)+':'+str(e))
  per={}
  for project,tasks in cycle_counts.items():
   per[project]=0
   for task,rs in tasks.items():
    if len(rs)!=2 or len({r['repeat'] for r in rs})!=2 or len({r['tests'] for r in rs})!=1:problems.append(str(path)+':REPEAT_COVERAGE:'+task)
    else:per[project]+=rs[0]['tests']
  if sum(per.values())!=receipt.get('checks_per_pass'):problems.append(str(path)+':TOTAL_COUNT')
  for project,value in per.items():counts[project]+=value
  cycles.append({'file':str(path),'sha256':sha(path),'checks_by_project':per,'checks_per_pass':sum(per.values()),'recorded_at_utc':receipt.get('recorded_at_utc')})
 carry=load(ROOT/'carryover-c09-validation.json');review=load(ROOT/'c09-pin-provenance-review.json');old=load(ROOT/'predecessor-run-state-original.json')
 for row in carry['results']:
  try:
   task=next(r for r in review['review'] if r['task']==row['task']);names=[n for n,h in review['inputs'][row['task']].items() if h==task['historically_observed_original']]
   if len(names)!=1:raise ValueError('CARRYOVER_ORIGINAL_NAME')
   initial=Path(old['output_ownership'][row['project']])/names[0];out=Path(row['output_directory'])/names[0]
   if sha(initial)!=task['historically_observed_original'] or sha(out)!=row['report_sha256'] or sem(load(initial))!=sem(load(out)):raise ValueError('CARRYOVER_INTEGRITY')
  except Exception as e:problems.append('CARRYOVER:'+str(e))
 current={p:sha(Path(p)) for p in state['protected_inputs']}
 changed=[p for p,h in state['protected_inputs'].items() if current[p]!=h]
 return {'cycles':cycles,'new_checks_by_project':counts,'new_checks_per_pass':sum(counts.values()),'verified_clean_reports':checked,
   'carried_over_checks_validated_in_R2':178,'predecessor_completed_checks':12364,'problems':problems,'control_inputs_changed':changed,
   'scope':'Artifact/hash/semantic audit only, not new source mechanism tests.'}

def processes(state):
 command='Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CreationDate,CommandLine | ConvertTo-Json -Depth 3'
 p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=15)
 if p.returncode:raise RuntimeError('PROCESS_CENSUS_UNAVAILABLE')
 items=json.loads(p.stdout);byid={int(x['ProcessId']):x for x in items};excluded={os.getpid()};parent=os.getpid()
 while parent in byid:
  parent=int(byid[parent]['ParentProcessId'])
  if not parent or parent in excluded:break
  excluded.add(parent)
 markers=[str(ROOT).lower(),state['run_id'].lower()]+[s.lower() for s in state['output_ownership'].values()]
 matched={int(x['ProcessId']) for x in items if int(x['ProcessId']) not in excluded and any(m in str(x.get('CommandLine') or '').lower() for m in markers)}
 while True:
  children={int(x['ProcessId']) for x in items if int(x['ParentProcessId']) in matched and int(x['ProcessId']) not in excluded}
  if children<=matched:break
  matched|=children
 return [{k:byid[pid].get(k) for k in ['ProcessId','ParentProcessId','Name','CreationDate']} for pid in sorted(matched)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--audit-only',action='store_true');ap.add_argument('--reason',choices=['DEADLINE_REACHED','SESSION_LIMIT','ALL_TASKS_BLOCKED','USER_STOP','APPROVED_SCOPE_COMPLETE']);args=ap.parse_args()
 path=ROOT/'run-state.json';raw=path.read_bytes();state=json.loads(raw);now=datetime.now(timezone.utc)
 result=audit(state);ps=processes(state)
 result.update(schema='OpenRemaster.R2TerminalAudit.v1',run_id=state['run_id'],observed_at_utc=now.isoformat(),deadline_utc=state['deadline_utc'],
   matching_run_processes=ps,process_observation_scope='Run command-line roots and their descendants; this audit/ancestors excluded.',
   mode=state['mode'],game_runtime_executed=False,live_leases_acquired=state['live_leases_acquired'])
 if args.audit_only:
  print(json.dumps(result,indent=2));return
 if not args.reason:raise RuntimeError('TERMINAL_REASON_REQUIRED')
 if args.reason=='DEADLINE_REACHED' and now<datetime.fromisoformat(state['deadline_utc']):raise RuntimeError('DEADLINE_NOT_REACHED')
 if ps:raise RuntimeError('OWNED_PROCESS_RECONCILIATION_REQUIRED')
 if state['live_leases_acquired']:raise RuntimeError('LEASE_RECONCILIATION_REQUIRED')
 result['terminal_reason']=args.reason;result['status']='PASS_INTEGRITY' if not result['problems'] and not result['control_inputs_changed'] else 'CLOSED_WITH_AUDIT_BLOCKERS'
 put(ROOT/'final-audit.json',result)
 terminal=dict(state,status='CLOSED_'+args.reason,observed_at_utc=now.isoformat(),terminalized_at_utc=now.isoformat(),
   final_audit_sha256=sha(ROOT/'final-audit.json'),final_audit_path=str(ROOT/'final-audit.json'),
   new_validated_checks=result['new_checks_per_pass'],carryover_validated_checks=178,
   continuous_execution_claim=False,active_owned_processes=[],next_action='Read final audit and explicit remaining gates before any newly authorized run.')
 put(ROOT/'PRETERMINAL_RUN_STATE.json',raw);put(ROOT/'TERMINAL_CHECKPOINT.json',terminal)
 lock=ROOT/'.state-cas.lock';lock.mkdir(exist_ok=False)
 try:
  if path.read_bytes()!=raw:raise RuntimeError('CONCURRENT_RUN_STATE_CHANGE')
  tmp=ROOT/'run-state.final.tmp';put(tmp,terminal);os.replace(tmp,path)
 finally:lock.rmdir()
 sys.path.insert(0,str(CP));from execution_journal import append_event
 append_event(ROOT/'execution-journal.jsonl',state['run_id'],'RUN_CLOSED',reason=args.reason,final_audit_sha256=sha(ROOT/'final-audit.json'),processes_found=0)
 put(ROOT/'CONTINUATION.json',{'run_id':state['run_id'],'state':terminal['status'],'deadline_utc':state['deadline_utc'],'final_audit_sha256':sha(ROOT/'final-audit.json'),
   'terminal_checkpoint_sha256':sha(ROOT/'TERMINAL_CHECKPOINT.json'),'no_processes_promised_after_response':True,'scope':'No automatic new four-hour budget.'})
 roots=[ROOT]+[Path(p) for p in state['output_ownership'].values()];entries=[]
 for root in roots:
  for f in sorted(root.rglob('*')):
   if f.is_file() and f.name!='final-manifest.json':entries.append({'root':str(root),'relative_path':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)})
 put(ROOT/'final-manifest.json',{'schema':'OpenRemaster.SealedEvidenceManifest.v1','run_id':state['run_id'],'terminal_reason':args.reason,'files':entries})
 print(json.dumps({'status':terminal['status'],'audit_status':result['status'],'new_checks_per_pass':result['new_checks_per_pass'],'carried_checks':178,
   'matching_run_processes':0,'final_audit_sha256':sha(ROOT/'final-audit.json'),'terminal_checkpoint_sha256':sha(ROOT/'TERMINAL_CHECKPOINT.json'),
   'manifest_sha256':sha(ROOT/'final-manifest.json'),'sealed_files':len(entries)},indent=2))
if __name__=='__main__':main()
