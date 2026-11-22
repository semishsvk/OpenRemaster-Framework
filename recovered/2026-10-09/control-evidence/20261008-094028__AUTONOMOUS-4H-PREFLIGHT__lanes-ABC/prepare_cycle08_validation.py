"""Bounded clean-repeat cycle for cross-profile distinction, conditional graph, attachment."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
cfg={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py','verify_callback_identity.py','verify_default_short_pixels.py','verify_short_perspective_pixels.py','verify_profile_noninterchangeability.py'],'data':[],
  'tests':[('verify_profile_noninterchangeability.py','profile-noninterchangeability-verification.json',43,'16afe320feb139454c0e2af583a9f68d31ab357ffa9a3a0307cb587737334e37')]},
 'OpenStonekeep':{'files':['build_conditional_turn_contract.py'],'data':['callback-verification.json','wrapper-delta-verification.json','turn-admission-verification.json','turn-first-frame-verification.json','heading-actor-commit-verification.json'],
  'tests':[('build_conditional_turn_contract.py','conditional-turn-contract-verification.json',83,'38e0d5a256a9fc5e85425fa649ea9868e7ba7f044e6f856475893213e960e317')]},
 'OpenUltima8':{'files':['ne_glob_candidates.py','verify_container_attachment.py'],'data':['ne_target_29_2adc.json','ne_target_29_2b36.json','map5-instance-ir.json'],
  'tests':[('verify_container_attachment.py','container-attachment-verification.json',116,'af2652b98a0f264c03aa96fd55aab5342db25ba94a21953188c9337cb7892ce0')]}}
old=ROOT/'validate_cycle06.py';s=old.read_text();a=s.index('CFG=');b=s.index('def sha(p):');s=s[:a]+'CFG='+repr(cfg)+'\n'+s[b:]
s=s.replace('cycle06','cycle08').replace('CYCLE06','CYCLE08').replace('C06','C08').replace("'cycle':6","'cycle':8").replace('1189','242')
needle="   unchanged=all(sha(lane/n)==h and sha(out/n)==h for n,h in pins[project].items());assert unchanged"
replace=needle+"\n   if project=='OpenStonekeep':\n    assert sha(out/'conditional-turn-contract.json')==sha(lane/'conditional-turn-contract.json')=='6831651d4bf36bffb607cf19a3be854faef25192086012e4cd9232387bf76cc2'"
assert s.count(needle)==1;s=s.replace(needle,replace)
with (ROOT/'validate_cycle08.py').open('x',encoding='utf-8') as f:f.write(s)
with (ROOT/'cycle08-harness-provenance.json').open('x',encoding='utf-8') as f:json.dump({'source_harness_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'tests_per_pass':242,'config':cfg,'extra_check':'Generated Stonekeep contract byte-identical to its sealed source hash in both repeats.'},f,indent=2)
