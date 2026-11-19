"""Portable source-only acceptance. No workers, game corpora, GUI or network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    paths=[ROOT/'development/glca',ROOT/'development/dual_trust',ROOT/'development/workflow']
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join(map(str,paths)))
    runs=[]
    for name,folder in [('glca',paths[0]/'tests'),('dual_trust',paths[1]),('workflow',paths[2])]:
        command=[sys.executable,'-B','-m','unittest','discover','-s',str(folder),'-v']
        p=subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=60,encoding='utf-8')
        raw=(p.stdout+p.stderr).encode();(args.out/(name+'.log')).write_bytes(raw)
        runs.append(dict(suite=name,exit_code=p.returncode,log=name+'.log',log_sha256=hashlib.sha256(raw).hexdigest()))
    from importlib import util
    # Import through the same explicit paths as child test runners.
    for path in paths:sys.path.insert(0,str(path))
    from glca.retail import corpus_manifest,validate_ir,solve_model,atlas,typed_state,FIELDS
    fixture=args.out/'synthetic-corpus';fixture.mkdir();(fixture/'fixture.dat').write_bytes(b'SYNTHETIC-ONLY-RESOURCE')
    corpus=corpus_manifest(fixture,project='SYNTHETIC')
    ref=dict(path='fixture.dat',sha256=corpus['files'][0]['sha256'],offset=0,length=8)
    ir=dict(schema='OpenRemaster.RLR.LogicIR.v1',project='SYNTHETIC',rooms=[dict(id='room',evidence_state='SOURCE_ONLY',source_refs=[ref])],objects=[],dialogues=[],puzzles=[],endings=[])
    model=solve_model(['start','win','trap'],[{'from':'start','to':'win','guard':True},{'from':'start','to':'trap','guard':None}],'start',['win'])
    output=atlas('SYNTHETIC',ir,corpus,model)
    (args.out/'synthetic-atlas.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    report=dict(schema='OpenRemaster.DevelopmentAcceptance.v1',status='PASS' if all(r['exit_code']==0 for r in runs) else 'FAIL',scope='SOURCE_AND_SYNTHETIC_ONLY',runs=runs,real_game_runtime=False,production_go=False)
    (args.out/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
