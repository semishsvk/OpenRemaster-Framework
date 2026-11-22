import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {dependency as baseline} from './support/local-dependencies.mjs';
import {createHash} from 'node:crypto';
import {readR8Fixture} from './support/r8-fixtures.mjs';
import {binding,response,now} from './project-fixture.mjs';
const ts=baseline('typescript');
const cache=new Map();
function load(url) {
  if(cache.has(url.href))return cache.get(url.href);
  const {outputText}=ts.transpileModule(readFileSync(url,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}});
  const module={exports:{}};new Function('require','module','exports',outputText)(n=>load(new URL(n+'.ts',url)),module,module.exports);cache.set(url.href,module.exports);return module.exports;
}
const {parseNativeFileObservation:parse,observationProjectInput:input,validateObservationBinding:validate}=load(new URL('../src/native-file-observation.ts',import.meta.url));
const {projectWorkspaceView}=load(new URL('../src/project-workspace-view.ts',import.meta.url));
test('synthetic exact binding projects current physical files but no gameplay/fidelity/authority',()=>{
  const b=binding(),p=input(parse(response(b),b,now),b,now),s=projectWorkspaceView({input:p,key:'selected'},'selected',now);
  assert.equal(s.phase,'LIVE');assert.ok(s.playableBuild);assert.equal(s.gameplay,'UNKNOWN');assert.equal(s.fidelity,'UNKNOWN');assert.equal(s.executionAuthority,false);assert.equal(s.executionAdmission,'UNKNOWN');
});
for(const [label,mutate] of [
  ['extra top field',r=>r.granted=true],['unknown schema',r=>r.schema='v2'],['authority',r=>r.execution_authority=true],['not readonly',r=>r.read_only=false],
  ['claimed gameplay',r=>r.gameplay='PASS'],['claimed fidelity',r=>r.fidelity='PASS'],['stale',r=>r.observed_epoch_ms=now-5001],['future',r=>r.observed_epoch_ms=now+1],['fractional time',r=>r.observed_epoch_ms=now-0.5],
  ['foreign project',r=>r.selection.project_id='Other'],['foreign edition',r=>r.selection.edition_id='RETAIL'],['foreign operation',r=>r.selection.committed_operation_id='9'.repeat(32)],['foreign manifest',r=>r.selection.accepted_manifest_digest='9'.repeat(64)],
  ['path in request',r=>r.selection.path='C:/other.exe'],['source commit',r=>r.source_commit='9'.repeat(40)],['source tree',r=>r.source_tree='9'.repeat(40)],['source manifest',r=>r.source_manifest_sha256='9'.repeat(64)],['build plan',r=>r.build_plan_sha256='9'.repeat(64)],['engine',r=>r.engine='other'],
  ['file hash',r=>r.files[0].sha256='9'.repeat(64)],['file bytes',r=>r.files[0].bytes++],['file byte boolean',r=>r.files[0].bytes=true],['file zero',r=>r.files[0].bytes=0],['file too big',r=>r.files[0].bytes=268435457],['file case mismatch',r=>r.files[0].name='game.exe'],
  ['absolute filename',r=>r.files[0].name='C:/Game.exe'],['relative filename',r=>r.files[0].name='../Game.exe'],['stream filename',r=>r.files[0].name='Game.exe:stream'],['reserved filename',r=>r.files[0].name='NUL.exe'],
  ['wrong role',r=>r.files[0].role='DLL'],['missing PCK',r=>r.files.pop()],['extra file',r=>r.files.push({...r.files[0]})],['duplicate role',r=>r.files[1].role='EXE'],['duplicate file identity',r=>r.files[1].file_id=r.files[0].file_id],['invalid volume',r=>r.files[0].volume='x'.repeat(16)],['invalid file ID',r=>r.files[0].file_id='4'.repeat(31)],['extra file path',r=>r.files[0].path='C:/Game.exe'],
]) test('native response rejects '+label,()=>{const b=binding(),r=response(b);mutate(r);assert.throws(()=>parse(r,b,now));});
test('producer HOLD accepts no files or authority',()=>{
  const b=binding(),r={schema:'OpenRemaster.NativeFileObservation.v1',state:'HOLD',read_only:true,execution_authority:false,gameplay:'UNKNOWN',fidelity:'UNKNOWN',observed_epoch_ms:now,reason:'NO_ACCEPTED_SELECTION'};
  assert.equal(input(parse(r,b,now),b,now),null);assert.throws(()=>parse({...r,files:[]},b,now));assert.throws(()=>parse({...r,reason:'APPROVED'},b,now));
});
test('request catalog itself must be complete and independent of response',()=>{
  for(const change of [b=>b.files=[],b=>b.request.edition_id='../DEMO',b=>b.files[1].sha256='bad',b=>b.files[0].bytes=Infinity,b=>b.requiresPck=false]) {
    const b=binding();change(b);assert.throws(()=>validate(b));
  }
  assert.throws(()=>parse(response(),null,now));assert.throws(()=>parse(JSON.stringify(response()),binding(),now));
});
test('cached selection cannot render LIVE under a new project, edition, build or manifest',()=>{
  const b=binding(),p=input(response(b),b,now),key=JSON.stringify(validate(b)),view={input:p,key};
  assert.equal(projectWorkspaceView(view,key,now).phase,'LIVE');
  for(const mutate of [n=>n.request.project_id='Other',n=>n.request.edition_id='RETAIL',n=>n.request.committed_operation_id='9'.repeat(32),n=>n.request.accepted_manifest_digest='9'.repeat(64),n=>n.sourceTree='9'.repeat(40)]) {
    const next=binding();mutate(next);assert.equal(projectWorkspaceView(view,JSON.stringify(validate(next)),now),null);
  }
  assert.equal(projectWorkspaceView(view,null,now),null);
});
test('cached physical evidence expires without a new producer response',()=>{
  const b=binding(),p=input(response(b),b,now),v={input:p,key:'same'};
  assert.ok(projectWorkspaceView(v,'same',now+5000).playableBuild);
  assert.equal(projectWorkspaceView(v,'same',now+5001).playableBuild,null);
  assert.equal(projectWorkspaceView(v,'same',now+5001).phase,'HOLD');
  assert.throws(()=>input(response(b),b,now+5001));
});
test('exact Python Win32 private-fixture response crosses the TypeScript boundary',()=>{
  const raw=readR8Fixture('r1.json');
  assert.equal(createHash('sha256').update(raw).digest('hex'),'39619dae718bbc4b3a20c6b659ef49e9419d1efd2ec27d5b9a77d72f19206554');
  const f=JSON.parse(raw),row=f.catalog[0];assert.equal(f.fixture_only,true);
  const sha=createHash('sha256').update('fixture only').digest('hex');
  // Expected bytes/hash are independent of the returned observation fields.
  const manifest='{"files": [{"bytes": 12, "name": "Fixture.exe", "sha256": "'+sha+'"}]}';
  assert.equal(createHash('sha256').update(manifest).digest('hex'),f.request.accepted_manifest_digest);
  const b={request:row.selection,engine:row.engine,sourceCommit:row.source_commit,sourceTree:row.source_tree,
    sourceManifestSha256:row.source_manifest_sha256,buildPlanSha256:row.build_plan_sha256,requiresPck:false,
    files:[{role:'EXE',name:'Fixture.exe',sha256:sha,bytes:12}]};
  assert.deepEqual(f.request,b.request);
  const result=parse(f.live,b,f.live.observed_epoch_ms);
  assert.equal(result.state,'LIVE');assert.equal(input(result,b,f.live.observed_epoch_ms).build.artifacts[0].sha256,sha);
  assert.equal(input(f.default_reply,b,f.default_reply.observed_epoch_ms),null);
  assert.throws(()=>parse(f.live,b,f.live.observed_epoch_ms+5001));
  assert.throws(()=>parse({...f.live,source_tree:'f'.repeat(40)},b,f.live.observed_epoch_ms));
});
test('exact R2 private WAL observation crosses the same DTO boundary without a live freshness claim',()=>{
  const raw=readR8Fixture('r2-wal.json');
  assert.equal(createHash('sha256').update(raw).digest('hex'),'2646a36b28108dacd6511f857adf7a18e099462bf5315cbeb2fde8bab86de4a6');
  const f=JSON.parse(raw),row=f.catalog[0];
  assert.equal(f.fixture_only,true);assert.equal(f.journal_mode,'wal');assert.equal(f.source_manifest_sha256,'0053942219c56f9434344bfe6e919b791a0d3815ee91081ae8ef56b981539a19');
  const hash=createHash('sha256').update('fixture only').digest('hex');
  const manifest='{"files": [{"bytes": 12, "name": "Fixture.exe", "sha256": "'+hash+'"}]}';
  assert.equal(f.request.accepted_manifest_digest,createHash('sha256').update(manifest).digest('hex'));
  const b={request:row.selection,engine:row.engine,sourceCommit:row.source_commit,sourceTree:row.source_tree,
    sourceManifestSha256:row.source_manifest_sha256,buildPlanSha256:row.build_plan_sha256,requiresPck:false,
    files:[{role:'EXE',name:'Fixture.exe',sha256:hash,bytes:12}]};
  const dto=parse(f.live,b,f.live.observed_epoch_ms),p=input(dto,b,f.live.observed_epoch_ms);
  assert.equal(p.build.artifacts[0].sha256,hash);assert.equal(p.gameplay,null);assert.equal(p.fidelity,null);assert.equal(p.admission,'UNKNOWN');
  assert.throws(()=>parse(f.live,b,f.live.observed_epoch_ms+5001));
  assert.throws(()=>parse({...f.live,selection:{...f.request,edition_id:'RETAIL'}},b,f.live.observed_epoch_ms));
});
