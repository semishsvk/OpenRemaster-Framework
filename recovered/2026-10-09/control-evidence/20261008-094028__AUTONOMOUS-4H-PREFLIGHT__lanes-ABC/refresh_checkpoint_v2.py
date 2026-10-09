"""Passive state checkpoint for the ongoing fixed-deadline work block."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent
PATH=ROOT/'run-state.json';state=json.loads(PATH.read_text());now=datetime.now(timezone.utc)
if now>=datetime.fromisoformat(state['deadline_utc']):raise SystemExit('DEADLINE_REACHED')
reports={
 'OpenMDK1':['CYCLE01_CHECKPOINT.json','depth-guard-verification.json','perspective-input-verification.json'],
 'OpenStonekeep':['CYCLE01_CHECKPOINT.json','callback-verification.json','wrapper-delta-verification.json'],
 'OpenUltima8':['CYCLE01_CHECKPOINT.json','materialization-receipt.json','reference-divergence.json','original-glob-verification.json']}
nexts={'OpenMDK1':'Perspective gradient setup and sign-dependent triangle width path.',
 'OpenStonekeep':'Default continuation to turn-intent state with explicit unknown event barriers.',
 'OpenUltima8':'Seal original +1 XY GLOB proof; produce corrected typed materialization evidence without applying upstream fixes.'}
for project,names in reports.items():
 p=Path(state['output_ownership'][project]);found={}
 for name in names:
  f=p/name
  if f.exists():
   d=json.loads(f.read_text());found[name]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'status':d.get('status'),'tests':d.get('tests'),'checkpoint':d.get('checkpoint')}
 state['lanes'][project].update(state='READ_ONLY_WORK_ACTIVE',active_owned_pid=None,completed_reports=found,next=nexts[project])
state['observed_at_utc']=now.isoformat();state['elapsed_seconds']=(now-datetime.fromisoformat(state['started_at_utc'])).total_seconds()
state['completed_cycle01_validation']={'receipt':str(ROOT/'cycle01-validation-receipt.json'),'sha256':hashlib.sha256((ROOT/'cycle01-validation-receipt.json').read_bytes()).hexdigest(),'status':'PASS'}
state['next_action']='Cycle02: source-backed perspective gradients, Stonekeep continuation, corrected original GLOB materialization; no completed-suite repetition without a new milestone.'
text=json.dumps(state,indent=2,sort_keys=True)
snapshot=ROOT/('checkpoint-'+now.strftime('%H%M%S')+'.json')
with snapshot.open('x',encoding='utf-8') as f:f.write(text)
temp=ROOT/'run-state.pending.json'
with temp.open('x',encoding='utf-8') as f:f.write(text);f.flush();os.fsync(f.fileno())
os.replace(temp,PATH)
sys.path.insert(0,r'F:\Remaster Framework\orchestrator\control-plane');from execution_journal import append_event
append_event(ROOT/'execution-journal.jsonl',state['run_id'],'CHECKPOINT_SAVED',checkpoint=str(snapshot),elapsed_seconds=state['elapsed_seconds'],mode='INTERLEAVED',new_heavy_jobs=0)
print(json.dumps({'utc':now.isoformat(),'elapsed_seconds':state['elapsed_seconds'],'deadline_utc':state['deadline_utc'],'checkpoint':str(snapshot),'new_heavy_jobs':0}))
