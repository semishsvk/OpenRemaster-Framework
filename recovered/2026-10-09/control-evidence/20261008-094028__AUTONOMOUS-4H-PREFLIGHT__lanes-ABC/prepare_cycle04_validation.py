"""Reuse the sealed finite validation harness with only the next evidence contracts."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
cfg={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py','verify_short_perspective_pixels.py'],'data':[],
  'script':'verify_short_perspective_pixels.py','report':'short-perspective-pixel-verification.json','tests':216,'pin':'6e438b18ebb9855ba74da0b3c25bb7da687ae0737d95672b805dd1cec1020074'},
 'OpenStonekeep':{'files':['source_manifest.py','le_fixups.py','verify_turn_intent.py','verify_ordinary_turn_envelope.py','verify_orientation_boundaries_v2.py'],'data':[],
  'script':'verify_orientation_boundaries_v2.py','report':'orientation-boundary-verification-v2.json','tests':23,'pin':'7d91ecbc2f3a2b8c0ba45148b2b1158925e7ace0661aa663bbf9a3894f225c0f'},
 'OpenUltima8':{'files':['ne_glob_candidates.py','verify_glob_creation_route.py'],'data':['creation-helper-targets.json','materialization-receipt.json'],
  'script':'verify_glob_creation_route.py','report':'glob-creation-route-verification.json','tests':2358,'pin':'a5f04649407b62e50744a0746c0ac14eaf7eb56d783d9942eb2cff4768e9e1c6'}}
old=ROOT/'validate_cycle03.py';s=old.read_text();a=s.index('CFG={');z=s.index('def sha(p):')
s=s[:a]+'CFG='+repr(cfg)+'\n'+s[z:]
s=s.replace('cycle03','cycle04').replace('C03','C04').replace("'cycle':3","'cycle':4").replace('2151','2597')
with (ROOT/'validate_cycle04.py').open('x',encoding='utf-8') as f:f.write(s)
with (ROOT/'cycle04-harness-provenance.json').open('x',encoding='utf-8') as f:json.dump({'source_harness_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'changes':'Task allowlist, report pins, output cycle names and exact test total only. Deadline/bounds/comparison unchanged.','tests_per_pass':2597,'config':cfg},f,indent=2)
