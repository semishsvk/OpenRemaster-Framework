import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {dependency as baseline} from './support/local-dependencies.mjs';
const ts = baseline('typescript');
function load(name) {
  const raw = readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8');
  const {outputText} = ts.transpileModule(raw, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}});
  const module = {exports:{}};
  new Function('module', 'exports', outputText)(module, module.exports);
  return module.exports;
}
const {parseProjectInput, artifactPath} = load('project-input');
const {projectState} = load('unified-project-state');
const now=1_800_000_000_000, identity={project:'FixtureProject',edition:'DEMO'};
function fixture() {
  const build={...identity,id:'fixture-only',commit:'a'.repeat(40),tree:'b'.repeat(40),engine:'fixture-engine',
    artifacts:[{role:'EXE',path:'dist/Game.exe',sha256:'c'.repeat(64)},{role:'PCK',path:'dist/Game.pck',sha256:'d'.repeat(64)}],requiresPck:true};
  return {...identity,archived:false,capturedAt:now,origin:'HOST_READONLY',
    sourceCheckpoint:{...identity,checkpoint:'fixture-only',commit:build.commit,tree:build.tree},build,
    observations:build.artifacts.map(a=>({...identity,buildId:build.id,...a,exists:true,checkedAt:now,source:'NATIVE_FILE_READ'})),
    gameplay:null,fidelity:null,writers:['fixture-existing-owner'],admission:'UNKNOWN',blockers:[],nextSafeTask:null};
}
test('strict fixture remains a read-only projection with UNKNOWN gameplay/fidelity/admission',()=>{
  const p=parseProjectInput(fixture(),identity,now), s=projectState(p,now);
  assert.equal(s.phase,'LIVE');assert.ok(s.playableBuild);assert.equal(s.gameplay,'UNKNOWN');
  assert.equal(s.fidelity,'UNKNOWN');assert.equal(s.executionAdmission,'UNKNOWN');assert.equal(s.executionAuthority,false);
});
for(const [label,mutate] of [
  ['extra authority',v=>v.executionAuthority=true],['unknown origin',v=>v.origin='REPORT'],
  ['identity edition',v=>v.edition='RETAIL'],['source edition',v=>v.sourceCheckpoint.edition='RETAIL'],
  ['build commit',v=>v.build.commit='e'.repeat(40)],['build tree',v=>v.build.tree='f'.repeat(40)],
  ['unknown role',v=>v.build.artifacts[0].role='DLL'],['missing PCK',v=>v.build.artifacts.pop()],
  ['extra file',v=>v.build.artifacts.push({...v.build.artifacts[0]})],
  ['duplicate path',v=>v.build.artifacts[1].path='DIST/GAME.EXE'],
  ['unknown nested field',v=>v.build.authorized=true],['bad SHA',v=>v.build.artifacts[0].sha256='C'.repeat(64)],
  ['future capture',v=>v.capturedAt=now+1],['stale capture',v=>v.capturedAt=now-10_001],
  ['fractional time',v=>v.capturedAt=now-0.5],['stale observation',v=>v.observations[0].checkedAt=now-10_001],
  ['foreign observation build',v=>v.observations[0].buildId='other'],
  ['foreign observation edition',v=>v.observations[0].edition='RETAIL'],
  ['duplicate observation',v=>v.observations[1]={...v.observations[0]}],
  ['missing observation hash',v=>v.observations[0].sha256=null],['boolean existence',v=>v.observations[0].exists=1],
  ['report observation',v=>v.observations[0].source='REPORT'],['unknown gate',v=>v.admission='APPROVED'],
  ['duplicate writer',v=>v.writers.push(v.writers[0])],['control text',v=>v.blockers=['reason\nspoof']],
]) test('rejects '+label,()=>{const v=fixture();mutate(v);assert.throws(()=>parseProjectInput(v,identity,now));});
for(const path of ['../game.exe','dist/../game.exe','C:/game.exe','//server/share/game.exe','\\\\?\\C:\\game.exe',
  'dist/game.exe:stream','dist//game.exe','dist/./game.exe','dist/NUL.exe','dist/COM1.pck','dist/game.exe.','dist/game.exe ']) {
  test('rejects unsafe path '+JSON.stringify(path),()=>assert.equal(artifactPath(path),false));
}
test('does not retain caller-owned nested arrays or objects',()=>{
  const v=fixture(), parsed=parseProjectInput(v,identity,now);v.build.artifacts[0].sha256='e'.repeat(64);v.blockers.push('changed');
  assert.equal(parsed.build.artifacts[0].sha256,'c'.repeat(64));assert.deepEqual(parsed.blockers,[]);
});
test('rejects sparse arrays and accessors without reading them',()=>{
  const v=fixture();v.observations=Array(1);assert.throws(()=>parseProjectInput(v,identity,now));
  const q=fixture();Object.defineProperty(q,'project',{get(){throw Error('getter executed');},enumerable:true});
  assert.throws(()=>parseProjectInput(q,identity,now),/PROJECT_INPUT_INVALID/);
  const a=fixture();Object.defineProperty(a.writers,0,{get(){throw Error('array getter executed');},enumerable:true});
  assert.throws(()=>parseProjectInput(a,identity,now),/PROJECT_INPUT_INVALID/);
});
test('missing physical file yields HOLD rather than playable or authority',()=>{
  const v=fixture();v.observations[0].exists=false;v.observations[0].sha256=null;
  const s=projectState(parseProjectInput(v,identity,now),now);assert.equal(s.phase,'HOLD');assert.equal(s.playableBuild,null);assert.equal(s.executionAuthority,false);
});
test('conflicting writers and failed admission stay HOLD',()=>{
  for(const change of [{writers:['one','two']},{admission:'FAIL'},{admission:'HOLD'},{admission:'BLOCKED'}]) {
    const s=projectState(parseProjectInput({...fixture(),...change},identity,now),now);assert.equal(s.phase,'HOLD');assert.equal(s.playableBuild,null);
  }
});
test('archived reports never expose playable artifacts',()=>{
  const v=fixture();v.archived=true;v.origin='ARCHIVED_REPORT';
  const s=projectState(parseProjectInput(v,identity,now),now);assert.equal(s.phase,'ARCHIVED');assert.equal(s.playableBuild,null);assert.equal(s.gameplay,'HOLD');
});
test('invalid clocks and overbroad freshness fail closed',()=>{
  for(const clock of [NaN,Infinity,-1,now+0.5]) assert.throws(()=>parseProjectInput(fixture(),identity,clock));
  for(const ttl of [0,-1,10_001,NaN,Infinity]) assert.throws(()=>parseProjectInput(fixture(),identity,now,ttl));
});
