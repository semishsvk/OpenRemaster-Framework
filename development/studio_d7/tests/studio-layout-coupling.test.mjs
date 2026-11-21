import assert from 'node:assert/strict';
import test from 'node:test';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {dependency} from './support/local-dependencies.mjs';
import {readR8Fixture} from './support/r8-fixtures.mjs';
const ts=dependency('typescript'),root=new URL('../',import.meta.url),cache=new Map();
function load(url){
 if(cache.has(url.href))return cache.get(url.href);
 const module={exports:{}},code=ts.transpileModule(readFileSync(url,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 new Function('require','module','exports',code)(name=>load(new URL(name+'.ts',url)),module,module.exports);
 cache.set(url.href,module.exports);return module.exports;
}
const {parseNativeFileObservation:parse,observationProjectInput:project}=load(new URL('src/native-file-observation.ts',root));
const {projectWorkspaceView}=load(new URL('src/project-workspace-view.ts',root));
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const raw=readR8Fixture('studio-wal.json'),f=JSON.parse(raw),manifestBytes=Buffer.from(f.manifest_bytes_hex,'hex');
const expectedDigest=hash(manifestBytes),expectedSHA=hash('fixture only'),at=f.live.observed_epoch_ms;
// Trusted expectation comes from pinned fixture/manifest plus known independent
// constants, never from the response being parsed or renderer-supplied paths.
const binding={request:{project_id:'Fixture',edition_id:'fixture_edition',committed_operation_id:'a'.repeat(32),accepted_manifest_digest:expectedDigest},
 engine:'fixture_engine',sourceCommit:'1'.repeat(40),sourceTree:'2'.repeat(40),sourceManifestSha256:'3'.repeat(64),buildPlanSha256:'4'.repeat(64),requiresPck:false,
 files:[{role:'EXE',name:'openremaster_studio_shadow.exe',bytes:12,sha256:expectedSHA}]};
test('saved private Studio WAL response and actual manifest cross unchanged v1 consumer without live freshness claim',()=>{
 assert.equal(f.fixture_only,true);assert.equal(raw.length,4916);assert.deepEqual(f.request,binding.request);
 const manifest=JSON.parse(manifestBytes);assert.equal(manifest.schema,'OpenRemaster.DevBuildArtifacts.v1');assert.equal(manifest.operation_id,'a'.repeat(32));
 assert.equal(manifest.studio_exe_sha256,expectedSHA);assert.equal(manifest.studio_exe_bytes,12);
 assert.equal(f.catalog[0].scenario,'build_studio_dev');assert.equal(f.catalog[0].artifact_layout,'studio-target-debug');assert.equal(f.catalog[0].artifact_schema,manifest.schema);
 const dto=parse(f.live,binding,at),p=project(dto,binding,at);
 assert.equal(dto.files.length,1);assert.equal(dto.files[0].role,'EXE');assert.equal(p.build.artifacts.length,1);assert.equal(p.build.artifacts[0].sha256,expectedSHA);
 assert.equal(p.admission,'UNKNOWN');assert.equal(p.gameplay,null);assert.equal(p.fidelity,null);
 const view=projectWorkspaceView({input:p,key:'fixture'},'fixture',at);assert.equal(view.phase,'LIVE');assert.equal(view.executionAuthority,false);
});
for(const [label,mutate] of [
 ['operation',x=>x.selection.committed_operation_id='b'.repeat(32)],['edition',x=>x.selection.edition_id='OTHER'],
 ['source tree',x=>x.source_tree='9'.repeat(40)],['manifest',x=>x.selection.accepted_manifest_digest='9'.repeat(64)],
 ['EXE bytes',x=>x.files[0].bytes++],['EXE hash',x=>x.files[0].sha256='9'.repeat(64)],
 ['renderer path',x=>x.files[0].path='target/debug/other.exe'],['authority',x=>x.execution_authority=true],
 ['alternate schema',x=>x.schema='OpenRemaster.NativeFileObservation.v2']
])test('Studio coupling rejects changed '+label,()=>{const value=structuredClone(f.live);mutate(value);assert.throws(()=>parse(value,binding,at));});
test('saved negative provider schema is HOLD; expired and future physical evidence cannot be LIVE',()=>{
 assert.equal(project(parse(f.wrong_catalog_schema,binding,f.wrong_catalog_schema.observed_epoch_ms),binding,f.wrong_catalog_schema.observed_epoch_ms),null);
 assert.throws(()=>parse(f.live,binding,at+5001));assert.throws(()=>parse(f.live,binding,at-1));
 assert.throws(()=>parse(JSON.stringify(f.live),binding,at));
});
test('transitive exact source pins are coupled and default catalog/binding remain empty',()=>{
 const entry=readFileSync(new URL('tools/r8-observation/entry.py',root)),producer=readFileSync(new URL('tools/r8-observation/producer.py',root)),files=readFileSync(new URL('tools/r8-observation/files.py',root));
 assert.equal(hash(producer),'1a6ff5cba8b331962677dc1851fd32defa1aeab495b2862bc5e633fa102dc085');
 assert.equal(hash(entry),'eb0631822500849f94cdfebc287dded5a958a08c555153e75b07804edbf84437');
 assert.equal(hash(files),'8750b1cf765caa4f5e8b0338caef98c10261905d74441f9d9868ac22bc98b996');
 assert.ok(entry.toString().includes('"producer": "'+hash(producer)+'"'));assert.ok(entry.toString().includes('"files": "'+hash(files)+'"'));
 const rust=readFileSync(new URL('src-tauri/src/file_observation.rs',root),'utf8');assert.ok(rust.includes('const ENTRY: &str = "'+hash(entry)+'"'));
 assert.match(producer.toString(),/EMPTY_CATALOG = b"\[\]"/);
 assert.match(readFileSync(new URL('src/App.tsx',root),'utf8'),/<ProjectWorkspace read=\{readNativeFileObservation\}\/>/);
 assert.match(readFileSync(new URL('src/ProjectWorkspace.tsx',root),'utf8'),/binding = null/);
});
