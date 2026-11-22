"""Reuse the finite three-lane clean-repeat harness, with corrected unique checkpoint names."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parent
cfg={
 'OpenMDK1':{'files':['static_probe.py','verify_f3_contract.py','verify_perspective_inputs.py','verify_perspective_span_inputs.py','verify_long_perspective_pixels.py'],'data':[],
  'script':'verify_long_perspective_pixels.py','report':'long-perspective-pixel-verification.json','tests':336,'pin':'d17de987b1fb273b2bed55486c4079ffbb0c39ea8308cb80aa7f158d642b069d'},
 'OpenStonekeep':{'files':['source_manifest.py','le_fixups.py','verify_turn_intent.py','verify_ordinary_turn_envelope.py','verify_heading_actor_commit.py'],'data':[],
  'script':'verify_heading_actor_commit.py','report':'heading-actor-commit-verification.json','tests':48,'pin':'b4d6cf6a68e54d1bbada072ed23d42bc42f05020a0e7bc1e59234854b2858d42'},
 'OpenUltima8':{'files':['ne_glob_candidates.py','verify_glob_item_constructor.py'],'data':['ne_target_28_f9b.json','original-glob-positions.json'],
  'script':'verify_glob_item_constructor.py','report':'glob-item-constructor-verification.json','tests':505,'pin':'744a001ed9ed1ed674fcf568c739b73cd644626618b69929d7b7a0c23c2dcbf7'}}
old=ROOT/'validate_cycle03.py';s=old.read_text();a=s.index('CFG={');b=s.index('def sha(p):');s=s[:a]+'CFG='+repr(cfg)+'\n'+s[b:]
s=s.replace('cycle03','cycle05').replace('CYCLE03','CYCLE05').replace('C03','C05').replace("'cycle':3","'cycle':5").replace('2151','889')
assert 'CYCLE03_CHECKPOINT' not in s and 'CYCLE05_CHECKPOINT' in s
with (ROOT/'validate_cycle05.py').open('x',encoding='utf-8') as f:f.write(s)
with (ROOT/'cycle05-harness-provenance.json').open('x',encoding='utf-8') as f:json.dump({'source_harness_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'config':cfg,'tests_per_pass':889,
 'checkpoint_filename_checked':'CYCLE05_CHECKPOINT.json','old_passes_not_rerun':True},f,indent=2)
