"""Pin and reuse only local helper-module dependency closures for the next tasks.
No module is executed here. New scripts write only their assigned R2 evidence root.
"""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'20261008-094028__AUTONOMOUS-4H-PREFLIGHT__lanes-ABC'
STARTS={
 'OpenMDK1':['verify_default_short_pixels.py','verify_default_chunk_lookahead.py'],
 'OpenStonekeep':['verify_turn_first_frame_gate.py','verify_ordinary_turn_envelope.py'],
 'OpenUltima8':['ne_glob_candidates.py']}
TASKS={
 'OpenMDK1':{'task':'DEFAULT_PERSPECTIVE_VARYING_Q_PIXEL_STREAM','hypothesis':'The verified q/uq/vq lookahead, per-interval slopes and persistent integer/fraction state reproduce the original default B flags0 pixels across nonaligned 32-pixel boundaries.',
 'negative':'Compare exact texel-read/write traces; independent full-perspective and endpoint-reset approximations must not silently substitute.'},
 'OpenStonekeep':{'task':'ORIGINAL_TURN_FRAME_STATE','hypothesis':'The first-frame request consumes source frame tables and changes a bounded identifiable rendering state before any external frame/effect callback.',
 'negative':'Unknown helper effects remain named barriers; frame request, completed frame and committed heading stay distinct.'},
 'OpenUltima8':{'task':'GLOB_POST_CONSTRUCTION_PLACEMENT','hypothesis':'The source record transform and ordinary constructor can be connected to original placement and flag changes without importing source-port lifecycle assumptions.',
 'negative':'Do not equate potential GLOB children with active world population; preserve any unverified calls as blockers.'}}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,v):
 with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,sort_keys=True)
def main():
 state=json.loads((ROOT/'run-state.json').read_text());old=json.loads((OLD/'run-state.json').read_text())
 assert datetime.now(timezone.utc)<datetime.fromisoformat(state['deadline_utc'])
 receipt=json.loads((ROOT/'carryover-c09-validation.json').read_text());assert receipt['status']=='PASS'
 allcopied={}
 for project,seeds in STARTS.items():
  src=Path(old['output_ownership'][project]);dst=Path(state['output_ownership'][project]);todo=list(seeds);done={}
  while todo:
   name=todo.pop()
   if name in done:continue
   if len(done)>24:raise RuntimeError('DEPENDENCY_BUDGET')
   p=src/name;raw=p.read_bytes();tree=ast.parse(raw.decode('utf-8-sig'),filename=name)
   for node in ast.walk(tree):
    mods=[node.module] if isinstance(node,ast.ImportFrom) and node.module else [n.name for n in node.names] if isinstance(node,ast.Import) else []
    for mod in mods:
     candidate=mod.split('.')[0]+'.py'
     if (src/candidate).is_file() and candidate not in done:todo.append(candidate)
   out=dst/name
   if out.exists():assert out.read_bytes()==raw
   else:
    with out.open('xb') as f:f.write(raw)
   done[name]=sha(p);assert sha(out)==done[name]
  record=dict(TASKS[project],schema='OpenRemaster.BoundedEvidenceJob.v1',run_id=state['run_id'],project=project,
    deadline_utc=state['deadline_utc'],source_module_hashes=done,reference_root=str(src),output_root=str(dst),
    mode='INTERLEAVED',input_authority='Canonical corpus hashes are enforced by reused readers; no live runtime claim.',
    budgets={'wall_seconds_per_test':30,'max_instruction_count_per_case':100000,'max_synthetic_memory_bytes':16*1024*1024,'new_heavy_jobs':0},
    permitted_writes='This new evidence directory only',source_worktree_writes=False,created_at_utc=datetime.now(timezone.utc).isoformat())
  put(dst/'phase01-job-contract.json',record);allcopied[project]=done
 put(ROOT/'phase01-module-reuse.json',allcopied)
 print(json.dumps({'status':'PREPARED','module_counts':{k:len(v) for k,v in allcopied.items()},'new_game_jobs':0},indent=2))
if __name__=='__main__':main()
