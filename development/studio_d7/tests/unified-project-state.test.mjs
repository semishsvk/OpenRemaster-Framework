import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync, mkdtempSync, writeFileSync, rmSync, existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createHash} from 'node:crypto';
import {dependency} from './support/local-dependencies.mjs';
const ts = dependency('typescript');
const raw = readFileSync(new URL('../src/unified-project-state.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(raw, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}});
const mod = {exports:{}};
new Function('exports', compiled.outputText)(mod.exports);
const {projectState} = mod.exports;
const now = 1_800_000_000_000;
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const identity = {project:'OpenExample',edition:'DEMO'};
function fixture() {
  const commit='a'.repeat(40), tree='b'.repeat(40);
  const artifacts=[{role:'EXE',path:'fixture/game.exe',sha256:digest('exe')},
    {role:'PCK',path:'fixture/game.pck',sha256:digest('pck')}];
  const build={...identity,id:'fixture-only',commit,tree,engine:'fixture-engine',artifacts,requiresPck:true};
  const verification={...identity,buildId:build.id,commit,tree,artifactHashes:artifacts.map(a=>a.sha256),
    evidenceSha256:digest('evidence'),status:'PASS',complete:true,checkedAt:now};
  return {...identity,archived:false,capturedAt:now,origin:'HOST_READONLY',
    sourceCheckpoint:{...identity,checkpoint:'fixture',commit,tree},build,
    observations:artifacts.map(a=>({...identity,buildId:build.id,...a,exists:true,checkedAt:now,source:'NATIVE_FILE_READ'})),
    gameplay:structuredClone(verification),fidelity:structuredClone(verification),writers:['existing-owner'],
    admission:'UNKNOWN',blockers:[],nextSafeTask:'Existing Host admission only'};
}
test('recent physical fixture keeps build, gameplay and fidelity separate',()=>{
  const p=fixture();p.fidelity.complete=false;
  const s=projectState(p,now);assert.equal(s.phase,'LIVE');assert.ok(s.playableBuild);
  assert.equal(s.gameplay,'PASS');assert.equal(s.fidelity,'HOLD');
  assert.equal(s.executionAuthority,false);assert.equal(s.executionAdmission,'UNKNOWN');
});
test('source-only snapshot never produces playable build',()=>{
  const p=fixture();p.build=null;p.observations=[];
  const s=projectState(p,now);assert.equal(s.phase,'LIVE');assert.equal(s.playableBuild,null);
  assert.equal(s.gameplay,'HOLD');assert.equal(s.lastVerifiedAt,null);
});
for(const role of ['EXE','PCK']) test(`missing physical ${role} is HOLD`,()=>{
  const p=fixture();p.observations.find(o=>o.role===role).exists=false;
  const s=projectState(p,now);assert.equal(s.phase,'HOLD');assert.equal(s.playableBuild,null);
});
test('fresh report alone cannot prove files exist',()=>{
  const p=fixture();p.observations=[];assert.equal(projectState(p,now).playableBuild,null);
  p.origin='ARCHIVED_REPORT';assert.equal(projectState(p,now).phase,'ARCHIVED');
});
test('SHA mismatch invalidates playable build',()=>{
  const p=fixture();p.observations[0].sha256='0'.repeat(64);
  assert.equal(projectState(p,now).phase,'HOLD');
});
for(const delta of [-10001,1]) test(`stale/future snapshot ${delta} is UNKNOWN`,()=>{
  const p=fixture();p.capturedAt+=delta;
  const s=projectState(p,now);assert.equal(s.phase,'UNKNOWN');assert.equal(s.playableBuild,null);
});
test('stale file read cannot inherit a fresh snapshot time',()=>{
  const p=fixture();p.observations[1].checkedAt-=10001;
  assert.equal(projectState(p,now).phase,'HOLD');
});
test('archived observations never become LIVE',()=>{
  const p=fixture();p.archived=true;const s=projectState(p,now);
  assert.equal(s.phase,'ARCHIVED');assert.equal(s.playableBuild,null);assert.equal(s.gameplay,'HOLD');
});
test('two conflicting writers remain HOLD even if admission reports PASS',()=>{
  const p=fixture();p.writers.push('another-owner');p.admission='PASS';
  const s=projectState(p,now);assert.equal(s.phase,'HOLD');assert.equal(s.executionAdmission,'HOLD');
});
for(const gate of ['HOLD','BLOCKED','FAIL']) test(`admission ${gate} cannot be upgraded`,()=>{
  const p=fixture();p.admission=gate;assert.equal(projectState(p,now).phase,'HOLD');
});
for(const part of ['sourceCheckpoint','build','observations','gameplay','fidelity'])
  test(`Demo/Retail mismatch in ${part} cannot pass`,()=>{
    const p=fixture();if(part==='observations')p.observations[0].edition='RETAIL';else p[part].edition='RETAIL';
    const s=projectState(p,now);
    if(part==='gameplay'||part==='fidelity')assert.equal(s[part],'HOLD');else assert.equal(s.playableBuild,null);
  });
test('verification tied to another source or artifact cannot pass',()=>{
  const p=fixture();p.gameplay.commit='c'.repeat(40);p.fidelity.artifactHashes[0]='d'.repeat(64);
  const s=projectState(p,now);assert.equal(s.gameplay,'HOLD');assert.equal(s.fidelity,'HOLD');
});
test('duplicate artifact roles and ambiguous native observations are rejected',()=>{
  const p=fixture();p.build.artifacts.push({...p.build.artifacts[0],path:'other.exe'});
  assert.equal(projectState(p,now).phase,'HOLD');
  const q=fixture();q.observations.push({...q.observations[0]});assert.equal(projectState(q,now).phase,'HOLD');
});
test('projection is deeply immutable and does not freeze or share caller data',()=>{
  const p=fixture();const s=projectState(p,now);p.build.artifacts[0].sha256='0'.repeat(64);
  assert.notEqual(s.playableBuild.artifacts[0].sha256,p.build.artifacts[0].sha256);
  assert.throws(()=>s.blockers.push('mutation'));assert.throws(()=>s.playableBuild.engine='changed');
});
test('no execution calls or K003 technical identifier changes',()=>{
  assert.doesNotMatch(raw,/\b(fetch|invoke|exec|spawn|sqlite|setInterval)\s*\(/);
  assert.doesNotMatch(raw,/ORCH-K003|scheduler/);
});
test('physical temporary-file readback detects deletion and later tampering',()=>{
  const root=mkdtempSync(join(tmpdir(),'openremaster-projection-'));
  try {
    const p=fixture();
    for(const a of p.build.artifacts){a.path=join(root,a.role.toLowerCase());writeFileSync(a.path,a.role.toLowerCase());}
    const observe=()=>p.observations=p.build.artifacts.map(a=>({...identity,buildId:p.build.id,
      role:a.role,path:a.path,exists:existsSync(a.path),sha256:existsSync(a.path)?digest(readFileSync(a.path)):null,
      checkedAt:now,source:'NATIVE_FILE_READ'}));
    observe();assert.ok(projectState(p,now).playableBuild);
    writeFileSync(p.build.artifacts[0].path,'tampered');observe();assert.equal(projectState(p,now).phase,'HOLD');
    rmSync(p.build.artifacts[1].path);observe();assert.equal(projectState(p,now).playableBuild,null);
  } finally {rmSync(root,{recursive:true,force:true});}
});
test('invalid freshness policy cannot widen LIVE window',()=>{
  for(const ttl of [NaN,0,-1,10001,Infinity])assert.throws(()=>projectState(fixture(),now,ttl));
});
