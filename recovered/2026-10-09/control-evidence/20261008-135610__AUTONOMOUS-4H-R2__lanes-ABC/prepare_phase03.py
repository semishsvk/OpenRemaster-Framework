from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
p=root/'validate_phase02.py'
s=p.read_text(encoding='utf-8')
start=s.index('TASKS=[')
end=s.index('\n\ndef sha(',start)
tasks=[
{'id':'profile-a-source-pixels','project':'OpenMDK1','report':'profile-a-source-pixel-verification.json','script':'verify_profile_a_source_pixels.py','tests':1341},
{'id':'actor-list-refresh','project':'OpenStonekeep','report':'actor-refresh-verification.json','script':'verify_actor_list_refresh.py','tests':151},
{'id':'projected-grid-predicate','project':'OpenUltima8','report':'projected-grid-verification-v2.json','script':'verify_projected_grid_predicate_v2.py','tests':768}]
for t in tasks:
 lane=Path(r'F:\Remaster Framework\output\projects')/t['project']/'evidence'/'20261008-135657__AUTONOMOUS-4H-R2__cycle01'
 t['pin']=hashlib.sha256((lane/t['report']).read_bytes()).hexdigest()
 assert json.loads((lane/t['report']).read_text())['tests']==t['tests']
s=s[:start]+'TASKS='+repr(tasks)+s[end:]
for a,b in [('phase02','phase03'),('PHASE02','PHASE03'),('R2-02','R2-03'),('1097','2260')]:
 s=s.replace(a,b)
# Preserve original dependency handling; no admission/permissions change.
out=root/'validate_phase03.py'
with out.open('x',encoding='utf-8') as f:f.write(s)
print(json.dumps({'script':str(out),'tasks':tasks},indent=2))
