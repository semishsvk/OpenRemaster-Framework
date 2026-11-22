"""Passive R2 checkpoint; never dispatches a process or extends the deadline."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
statepath=ROOT/'run-state.json';prior=statepath.read_bytes();s=json.loads(prior);now=datetime.now(timezone.utc)
assert s['run_id']=='AUTONOMOUS4H-R2-20261008T115609Z-ABC'
if now>=datetime.fromisoformat(s['deadline_utc']):raise SystemExit('DEADLINE_REACHED: seal terminal state, do not dispatch')
for project,root in s['output_ownership'].items():
 p=Path(root);reports={}
 for f in sorted(p.glob('*.json')):
  if 'verification' not in f.name and 'CHECKPOINT' not in f.name:continue
  r=load(f)
  if 'status' in r:reports[f.name]={'sha256':sha(f),'reported_status':r['status'],'tests':r.get('tests'),'recorded_at_utc':r.get('created_at_utc')}
 s['lanes'][project]['observed_reports']=reports
 s['lanes'][project]['state']='INTERLEAVED_EVIDENCE_WORK'
s['observed_at_utc']=now.isoformat();s['elapsed_seconds']=(now-datetime.fromisoformat(s['started_at_utc'])).total_seconds()
s['next_action']=sys.argv[1] if len(sys.argv)>1 else 'Continue next bounded unclosed gate fairly across the three lanes; use sealed cycle receipts, not initial PASS alone.'
s['validated_carryover']={'receipt':str(ROOT/'carryover-c09-validation.json'),'sha256':sha(ROOT/'carryover-c09-validation.json'),'cases':178,'scope':'Validated in R2, not backdated to R1'}
s['sealed_cycles']={p.name:sha(p) for p in sorted(ROOT.glob('phase*-validation.json'))}
text=(json.dumps(s,indent=2,sort_keys=True)+'\n').encode()
snapshot=ROOT/('checkpoint-'+now.strftime('%H%M%S')+'.json')
with snapshot.open('xb') as f:f.write(text)
lock=ROOT/'.state-cas.lock';lock.mkdir(exist_ok=False)
try:
 if statepath.read_bytes()!=prior:raise RuntimeError('CONCURRENT_STATE_WRITER')
 temp=ROOT/'run-state.checkpoint.tmp'
 with temp.open('xb') as f:f.write(text);f.flush();os.fsync(f.fileno())
 os.replace(temp,statepath)
finally:lock.rmdir()
sys.path.insert(0,str(CP));from execution_journal import append_event
append_event(ROOT/'execution-journal.jsonl',s['run_id'],'CHECKPOINT_SAVED',checkpoint=str(snapshot),sha256=sha(snapshot),mode=s['mode'])
print(json.dumps({'utc':now.isoformat(),'deadline_utc':s['deadline_utc'],'elapsed_seconds':s['elapsed_seconds'],'state_sha256':sha(statepath),'sealed_cycles':list(s['sealed_cycles']),'new_heavy_jobs':s['new_heavy_jobs']}))
