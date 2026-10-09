"""Next finite proof cycle: exact chunk continuity, first-frame gate, source population."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
cfg={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py','verify_default_chunk_continuity.py'],'data':[],
  'script':'verify_default_chunk_continuity.py','report':'default-chunk-continuity-verification.json','tests':672,'pin':'4e4e728fcd0f86c42fae5265b9ec022c4b3962b7d41ed7f6ac4e8917cd1ef97a'},
 'OpenStonekeep':{'files':['source_manifest.py','le_fixups.py','verify_turn_intent.py','verify_ordinary_turn_envelope.py','verify_turn_first_frame_gate.py'],'data':[],
  'script':'verify_turn_first_frame_gate.py','report':'turn-first-frame-verification.json','tests':72,'pin':'9f13a1bf1b24a76fe5758618f3216053c5000c7223c825fbde0381ae15cae240'},
 'OpenUltima8':{'files':['ne_glob_candidates.py','verify_record_population.py'],'data':['ne_target_29_f70.json','materialization-receipt.json','map5-instance-ir.json'],
  'script':'verify_record_population.py','report':'record-population-verification.json','tests':2867,'pin':'33755d25a537e9fddec9df3f57902e5c4ab4aa9ca8fdc39de18e8ab5ff0ef30e'}}
old=ROOT/'validate_cycle05.py';s=old.read_text();a=s.index('CFG=');b=s.index('def sha(p):');s=s[:a]+'CFG='+repr(cfg)+'\n'+s[b:]
s=s.replace('cycle05','cycle07').replace('CYCLE05','CYCLE07').replace('C05','C07').replace("'cycle':5","'cycle':7").replace('889','3611')
assert 'CYCLE07_CHECKPOINT' in s and 'CYCLE05_CHECKPOINT' not in s
with (ROOT/'validate_cycle07.py').open('x',encoding='utf-8') as f:f.write(s)
with (ROOT/'cycle07-harness-provenance.json').open('x',encoding='utf-8') as f:json.dump({'source_harness_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'config':cfg,'tests_per_pass':3611,'new_tasks_only':True,'per_process_timeout_seconds':30},f,indent=2)
