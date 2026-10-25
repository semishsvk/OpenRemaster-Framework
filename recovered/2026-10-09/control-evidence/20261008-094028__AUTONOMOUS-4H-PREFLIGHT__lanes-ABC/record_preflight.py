"""Record the user's current finite work block; never dispatch or alter live jobs."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,sys,os
ROOT=Path(__file__).resolve().parent
CP=Path(r'F:\Remaster Framework\orchestrator\control-plane')
START=datetime.fromisoformat('2026-10-08T07:39:23.845443+00:00')
DEADLINE=START+timedelta(hours=4)
RUN='AUTONOMOUS4H-20261008T073923Z-ABC'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
old=read(CP/'portfolio-lanes-20261008-v3.json')
assert old['policy']['temporary_focus_lane_ids']==['OpenMDK1','OpenStonekeep','OpenUltima8']
now=datetime.now(timezone.utc)
assert START<=now<DEADLINE
paths={name:rf'F:\Remaster Framework\output\projects\{name}\evidence\20261008-094213__AUTONOMOUS-4H__cycle01' for name in old['policy']['temporary_focus_lane_ids']}
protected={str(CP/n):sha(CP/n) for n in ['portfolio-lanes-20261008-v3.json','capabilities.json','worker-commissioning.json','orch_k003.py','leases.py','execution_journal.py']}
state={'schema':'OpenRemaster.AutonomousBlockState.v1','run_id':RUN,'started_at_utc':START.isoformat(),
 'deadline_utc':DEADLINE.isoformat(),'observed_at_utc':now.isoformat(),'status':'ACTIVE',
 'mode':'INTERLEAVED','requested_duration_hours':4,'max_lane_workers':3,'max_heavy_global':3,
 'checkpoint_interval_seconds':900,'shutdown_reserve_seconds':300,'max_repairs_without_new_evidence':2,
 'tool_capabilities':{'RDC_file_read':True,'RDC_process_exec':True,'subagent_delegation_exposed':False,
 'codex_on_PATH':False,'model_routing_exposed':False},
 'capacity_gate':'UNKNOWN_GLOBAL_OWNED_RESOURCE_CAPACITY; NO_NEW_HEAVY_EXECUTION',
 'native_worker_gate':read(CP/'worker-commissioning.json')['workers'].get('HomePC-NativeWorker'),
 'work_scope':'Read-only source/evidence review and sequential small bounded isolated proof scripts; no production runtime/build/capture.',
 'new_heavy_jobs':0,'new_native_game_jobs':0,'new_gpu_jobs':0,
 'existing_processes_untouched':True,'live_leases_acquired':[],'source_worktree_write_permission':False,
 'output_ownership':paths,'protected_inputs':protected,'focus_ids':list(paths),
 'scope_exclusions':['No Azrael polling','Demo CLOSED','Retail PAUSED','No ACL/account/service/automation changes'],
 'lanes':{name:{'state':'PREFLIGHT','output':p,'active_owned_pid':None} for name,p in paths.items()},
 'next_action':'Read the newer MDK 004 receipt, Stonekeep E.15-E.17 evidence and U8 materialization decoders; execute one bounded proof per lane before a new cycle.'}
with (ROOT/'run-state.json').open('x',encoding='utf-8') as f:json.dump(state,f,indent=2,sort_keys=True)
sys.path.insert(0,str(CP));from execution_journal import append_event
append_event(ROOT/'execution-journal.jsonl',RUN,'PREFLIGHT_RECORDED',mode=state['mode'],deadline_utc=state['deadline_utc'],new_heavy_jobs=0)
for name,path in paths.items():
 with (Path(path)/'block-link.json').open('x',encoding='utf-8') as f:json.dump({'run_id':RUN,'started_at_utc':state['started_at_utc'],'deadline_utc':state['deadline_utc'],'coordinator_state':str(ROOT/'run-state.json'),'owner_scope':'THIS_NEW_EVIDENCE_DIRECTORY_ONLY','project':name,'worktree_writes':False},f,indent=2)
print(json.dumps({'run_id':RUN,'started_at_utc':state['started_at_utc'],'deadline_utc':state['deadline_utc'],'mode':state['mode'],'state_sha256':sha(ROOT/'run-state.json'),'new_heavy_jobs':0},indent=2))
