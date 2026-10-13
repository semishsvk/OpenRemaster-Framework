"""Reuse the completed finite validation harness for three new pinned proof tasks."""
from pathlib import Path
import hashlib,json,ast,pprint
ROOT=Path(__file__).resolve().parent
p=ROOT/'validate_phase01.py';raw=p.read_bytes();s=raw.decode('utf-8')
tasks=[
 {'project':'OpenMDK1','id':'wrapped-source-pixels','script':'verify_wrapped_source_pixels.py','report':'wrapped-source-pixel-verification.json','tests':640,'pin':'d8bad5e2184197ecc87ad32ac97d9434723418a6f5c5a2d7524672dab2d84b68'},
 {'project':'OpenStonekeep','id':'frame-prefix-chain','script':'verify_frame_prefix_chain_v2.py','report':'frame-prefix-chain-verification-v2.json','tests':197,'pin':'8a90012134c0eb018e9f8d64d88964e64f0f12c20b514cb9fd7af3d7a0f094ce'},
 {'project':'OpenUltima8','id':'holding-world-placement','script':'verify_holding_world_placement.py','report':'holding-world-placement-verification.json','tests':260,'pin':'200af772c3365efda62ef9e606a8f5b2e5492be671df3ed82aaecf7bbd16916e'}]
a=s.index('TASKS=[');b=s.index('\ndef sha(',a)
s=s[:a]+'TASKS='+pprint.pformat(tasks,width=150)+'\n'+s[b:]
a=s.index("  if t['project']=='OpenUltima8':");b=s.index(" put(ROOT/'phase01-inputs.json'",a)
s=s[:a]+'''  if t['project']=='OpenMDK1':
   old_ir=Path(old['output_ownership']['OpenMDK1']).parent/'20261008-074645__MDK1-ALIAS-ACTIVE__bounded-v1'/'material-binding-sourceir.json'
   assert sha(old_ir)=='b597a9f27d5e03b34117d02d893a6e8b456406c8d413a2dd73276e96db32e783'
   inputs[t['id']]['relative_fixture']={'directory':'20261008-074645__MDK1-ALIAS-ACTIVE__bounded-v1','source':str(old_ir),'sha256':sha(old_ir)}
'''+s[b:]
s=s.replace('phase01','phase02').replace('PHASE01','PHASE02').replace('R2-01','R2-02').replace('1190','1097')
ast.parse(s)
with (ROOT/'validate_phase02.py').open('x',encoding='utf-8') as f:f.write(s)
with (ROOT/'phase02-harness-provenance.json').open('x',encoding='utf-8') as f:json.dump({'source_harness_sha256':hashlib.sha256(raw).hexdigest(),'new_harness_sha256':hashlib.sha256(s.encode()).hexdigest(),'tasks':tasks,'validation_conditions_unchanged':True,'changes':'New independently observed proof pins and the exact required MDK sourceIR relative fixture; no repeat/semantic/exit checks relaxed.'},f,indent=2)
assert p.read_bytes()==raw
print('Prepared R2 phase02, 1097 cases per complete pass.')
