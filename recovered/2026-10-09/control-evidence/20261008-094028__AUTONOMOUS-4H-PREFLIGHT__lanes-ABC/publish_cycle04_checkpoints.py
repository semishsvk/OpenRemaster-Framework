"""Finish publication after an exclusive-create name collision, without rerunning tests.
The prior C03 checkpoint and all original validation outputs remain unchanged.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent
from validate_cycle04 import CFG

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):
 with p.open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,sort_keys=True)
s=json.loads((ROOT/'run-state.json').read_text());r=json.loads((ROOT/'cycle04-validation.json').read_text())
assert r['status']=='PASS' and r['checks_per_pass']==2597 and len(r['results'])==6
for row in r['results']:
 assert row['status']=='PASS' and row['process_exited'] and row['exit_code']==0 and row['semantic_report_equal']
 lane=Path(s['output_ownership'][row['project']]);cfg=CFG[row['project']]
 assert sha(lane/row['repeat']/cfg['report'])==row['report_sha256']
for path,h in s['resume_input_hashes'].items():assert sha(Path(path))==h
prior={p:sha(Path(s['output_ownership'][p])/'CYCLE03_CHECKPOINT.json') for p in CFG}
for project,c in CFG.items():
 lane=Path(s['output_ownership'][project]);assert sha(lane/c['report'])==c['pin']
 put(lane/'CYCLE04_CHECKPOINT.json',{'schema':'OpenRemaster.LaneEvidenceCheckpoint.v1','run_id':s['run_id'],'checkpoint':s['run_id']+'-'+project+'-C04','project':project,
  'status':'PASS','checks_per_pass':c['tests'],'initial_report_sha256':c['pin'],'report':c['report'],'source_hashes':r['source_hashes'][project],
  'clean_repetitions':[x for x in r['results'] if x['project']==project],'scope':'SOURCE_MECHANISM_NOT_FULL_RUNTIME',
  'coordinator_receipt_sha256':sha(ROOT/'cycle04-validation.json'),'publication_note':'Recovered from wrong target filename in reusable harness; existing C03 file was not overwritten.'})
assert all(sha(Path(s['output_ownership'][p])/'CYCLE03_CHECKPOINT.json')==h for p,h in prior.items())
put(ROOT/'cycle04-publication-recovery.json',{'status':'PASS','original_publication':'BLOCKED_FILE_EXISTS','bad_target':'CYCLE03_CHECKPOINT.json','correct_target':'CYCLE04_CHECKPOINT.json',
 'failed_harness_sha256':sha(ROOT/'validate_cycle04.py'),'validation_was_completed':True,'validation_rerun':False,'checks_per_pass':2597,'all_six_clean_repeats_hash_verified':True,
 'prior_C03_unchanged':prior,'validation_receipt_sha256':sha(ROOT/'cycle04-validation.json'),'created_at_utc':datetime.now(timezone.utc).isoformat()})
print(json.dumps({'status':'PASS','checks_per_pass':2597,'clean_repeats_per_lane':2,'checkpoint_publication':'RECOVERED_WITHOUT_OVERWRITE_OR_TEST_RERUN','validation_sha256':sha(ROOT/'cycle04-validation.json'),'recovery_sha256':sha(ROOT/'cycle04-publication-recovery.json'),'utc':datetime.now(timezone.utc).isoformat()},indent=2))
