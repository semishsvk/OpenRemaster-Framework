"""Offline code-only review entry point. No worker, signer or live provider."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def verify_package():
    document=json.loads((ROOT/'MANIFEST.json').read_text(encoding='utf-8'))
    expected=set()
    for row in document['files']:
        name=row['path'];raw=ROOT/name;p=raw.resolve()
        if name in expected or not p.is_relative_to(ROOT) or raw.is_symlink() or not p.is_file():raise ValueError('PACKAGE_PATH_INVALID')
        expected.add(name)
        if p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('PACKAGE_SOURCE_DRIFT:'+name)
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual!=expected|{'MANIFEST.json'}:raise ValueError('UNDECLARED_PACKAGE_FILES')
    if document.get('production_go') is not False:raise ValueError('PACKAGE_SCOPE_INVALID')
    return len(expected)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path);parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    count=verify_package()
    if args.verify_only:
        print(json.dumps(dict(status='SOURCE_BYTES_VERIFIED_NOT_ACCEPTANCE',files=count,production_go=False)));return 0
    if args.out is None:parser.error('--out is required for tests')
    out=args.out.resolve()
    if out.is_relative_to(ROOT):raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_SOURCE_PACKAGE')
    out.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(ROOT/'lab'),str(ROOT/'production-owner-authority-v1'),str(ROOT/'framework'),str(ROOT/'tests')]
    import pytest
    tests=['test_resource_witness.py','test_m012_independent_head_witness.py','test_witness_key_separation.py','test_resource_anchor.py','test_anchor.py','test_resource_integrity.py','test_resource_transaction.py','test_resource_observation.py','test_work_identity.py','test_admission_shadow.py','test_governor.py']
    result=pytest.main(['-c',str(ROOT/'pytest.ini'),'--rootdir='+str(ROOT),'--confcutdir='+str(ROOT),*[str(ROOT/'tests'/t) for t in tests],'-q','--junitxml='+str(out/'review.xml'),'--basetemp='+str(out/'temp'),'-o','cache_dir='+str(out/'cache')])
    names=['admission_boundary_base','admission_shadow','authority','resource_authority','work_identity','resource_observation','resource_transaction','resource_anchor','resource_witness','governor','scope','anchor','openremaster.m005_anchor_contract','openremaster.m010_durable_recovery','openremaster.m011_signed_recovery','openremaster.m012_independent_head_witness']+[Path(t).stem for t in tests]+['test_m011_signed_recovery']
    imports=[]
    for name in names:
        module=sys.modules.get(name);path=Path(getattr(module,'__file__','')).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('NONPORTABLE_IMPORT:'+name)
        imports.append(dict(module=name,path=path.relative_to(ROOT).as_posix()))
    verify_package()
    (out/'IMPORTS.json').write_text(json.dumps(imports,indent=2)+'\n',encoding='utf-8')
    summary=dict(status='PASS' if result==0 else 'FAIL',source_files=count,scope='OFFLINE_SYNTHETIC_REVIEW_ONLY',imports_within_package=True,worker_started=False,independent_authority_verified=False,production_go=False)
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary));return int(result)

if __name__=='__main__':raise SystemExit(main())
