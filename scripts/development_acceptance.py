"""Portable source-only acceptance. No workers, game corpora, GUI or network."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent

def studio_offline(args):
    """One explicit light lane through this existing common entrypoint."""
    studio=ROOT/'development/studio_d7'
    if args.studio_deps_root is None or args.studio_node is None:
        raise ValueError('STUDIO_OFFLINE_EXPLICIT_INPUTS_REQUIRED')
    import shutil
    node=shutil.which(str(args.studio_node))
    if node is None:raise ValueError('STUDIO_NODE_UNAVAILABLE')
    env=dict(os.environ)
    for key in list(env):
        if key.upper().startswith('NODE_') or key.upper() in ('STUDIO_TYPESCRIPT','STUDIO_NODE_MODULES'):
            env.pop(key)
    commands=[('studio-staging',['git','ls-files','-z','--','development/studio_d7/.studio-test-deps',':(glob)development/studio_d7/.studio-test-deps.provision-*/**','development/studio_d7/test-results']),
              ('studio-pool',[node,str(studio/'tools/provision-offline-test-deps.mjs'),'--source',str(args.studio_deps_root.resolve())]),
              ('studio-source',[node,str(studio/'tools/run-source-checks.mjs'),'--cohort','ups'])]
    runs=[]
    for name,command in commands:
        # Inner runner has three 45s limits. Leave startup/reporting headroom.
        # subprocess.run kills its direct child on timeout; descendants are not
        # claimed stopped. The enclosing CI job remains the final isolation bound.
        timed_out=False
        try:
            result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=180)
            stdout,stderr,exit_code=result.stdout,result.stderr,result.returncode
        except subprocess.TimeoutExpired as error:
            timed_out=True
            stdout=error.stdout or b''
            stderr=(error.stderr or b'')+b'\nSTUDIO_PHASE_TIMEOUT_DIRECT_CHILD_ONLY\n'
            exit_code=None
        for stream,raw in (('stdout',stdout),('stderr',stderr)):
            (args.out/(name+'.'+stream)).write_bytes(raw)
        passed=not timed_out and exit_code==0 and (name!='studio-staging' or not stdout)
        runs.append(dict(suite=name,exit_code=exit_code,passed=passed,
            timed_out=timed_out,timeout_seconds=180,descendant_cleanup_guaranteed=False,
            stdout_sha256=hashlib.sha256(stdout).hexdigest(),stderr_sha256=hashlib.sha256(stderr).hexdigest()))
        if not passed:break
    report=dict(schema='OpenRemaster.DevelopmentAcceptance.v1',
        status='PASS' if len(runs)==3 and all(row['passed'] for row in runs) else 'FAIL',
        scope='STUDIO_OFFLINE_SOURCE_ONLY',entrypoint='scripts/development_acceptance.py',runs=runs,
        original_common_suites_executed=False,network_or_install=False,native_build=False,GUI=False,
        real_game_runtime=False,production_go=False)
    (args.out/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report));return 0 if report['status']=='PASS' else 1

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--studio-offline-only',action='store_true')
    parser.add_argument('--studio-deps-root',type=Path)
    parser.add_argument('--studio-node')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    if args.studio_offline_only:return studio_offline(args)
    if args.studio_deps_root is not None or args.studio_node is not None:
        raise ValueError('STUDIO_OPTIONS_REQUIRE_OFFLINE_ONLY')
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
