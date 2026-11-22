"""Update only this resumed work block's journal and checkpoint at safe boundaries."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;P=ROOT/'run-state.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=json.loads(P.read_text());now=datetime.now(timezone.utc)
if now>=datetime.fromisoformat(state['deadline_utc']):raise SystemExit('DEADLINE_REACHED')
if any(sha(Path(p))!=h for p,h in state['resume_input_hashes'].items()):raise RuntimeError('CONTROL_EPOCH_CHANGED')
NAMES={'OpenMDK1':['PENDING_MILESTONE_SEALED.json','signed-width-verification.json'],
 'OpenStonekeep':['turn-intent-verification.json'],
 'OpenUltima8':['PENDING_MILESTONE_SEALED.json','materialization-v3b-verification.json']}
for project,names in NAMES.items():
 lane=state['lanes'][project];root=Path(lane['output'])
 for name in names:
  path=root/name
  if path.exists():
   d=json.loads(path.read_text());lane['completed_reports'][name]={'sha256':sha(path),'status':d.get('status'),'tests':d.get('tests')}
 lane['active_owned_pid']=None;lane['state']='INTERLEAVED_EVIDENCE_WORK'
state['observed_at_utc']=now.isoformat();state['elapsed_seconds']=(now-datetime.fromisoformat(state['started_at_utc'])).total_seconds()
state['resumed_wall_seconds']=(now-datetime.fromisoformat(state['resumed_at_utc'])).total_seconds()
state['newest_cycle_note']='Pending 855 tests sealed with two clean repeats. New all-lane work: signed-width, turn-intent and corrected Map5 v3 IR.'
state['completed_pending_validation_sha256']=sha(ROOT/'cycle02-pending-validation.json')
blob=json.dumps(state,indent=2,sort_keys=True);snapshot=ROOT/('checkpoint-'+now.strftime('%H%M%S')+'.json')
with snapshot.open('x',encoding='utf-8') as f:f.write(blob)
tmp=ROOT/'run-state.update.tmp'
with tmp.open('x',encoding='utf-8') as f:f.write(blob);f.flush();os.fsync(f.fileno())
os.replace(tmp,P)
sys.path.insert(0,r'F:\Remaster Framework\orchestrator\control-plane');from execution_journal import append_event
append_event(ROOT/'execution-journal.jsonl',state['run_id'],'CHECKPOINT_SAVED',checkpoint=str(snapshot),mode='INTERLEAVED',deadline_utc=state['deadline_utc'])
print(json.dumps({'utc':now.isoformat(),'deadline_utc':state['deadline_utc'],'resumed_wall_seconds':state['resumed_wall_seconds'],'checkpoint':str(snapshot)}))
