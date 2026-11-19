"""Passive checkpoint update for this one user-requested block. No dispatch."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent
p=ROOT/'run-state.json';state=json.loads(p.read_text());now=datetime.now(timezone.utc)
if now>datetime.fromisoformat(state['deadline_utc']):raise SystemExit('DEADLINE_REACHED')
for lane in state['lanes'].values():
 out=Path(lane['output']);reports={}
 for n in ['depth-guard-verification.json','callback-verification.json','materialization-receipt.json']:
  f=out/n
  if f.exists():
   r=json.loads(f.read_text());reports[n]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'status':r.get('status'),'tests':r.get('tests')}
 lane['completed_reports']=reports
 lane['state']='READ_ONLY_WORK_ACTIVE'
 lane['active_owned_pid']=None
state['observed_at_utc']=now.isoformat();state['elapsed_seconds']=(now-datetime.fromisoformat(state['started_at_utc'])).total_seconds()
state['next_action']='Stonekeep callback delta and Ultima8 parent/materialization; MDK depth-guard new result awaits independent review/clean repeat.'
data=json.dumps(state,indent=2,sort_keys=True)
checkpoint=ROOT/('checkpoint-'+now.strftime('%H%M%S')+'.json')
with checkpoint.open('x',encoding='utf-8') as f:f.write(data)
tmp=ROOT/'run-state.next.json'
with tmp.open('x',encoding='utf-8') as f:f.write(data);f.flush();os.fsync(f.fileno())
os.replace(tmp,p)
sys.path.insert(0,r'F:\Remaster Framework\orchestrator\control-plane');from execution_journal import append_event
append_event(ROOT/'execution-journal.jsonl',state['run_id'],'CHECKPOINT_SAVED',checkpoint=str(checkpoint),elapsed_seconds=state['elapsed_seconds'],mode=state['mode'],new_heavy_jobs=0)
print(json.dumps({'utc':now.isoformat(),'elapsed_seconds':state['elapsed_seconds'],'checkpoint':str(checkpoint),'mode':state['mode']}))
