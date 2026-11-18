import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import test from 'node:test';
import ts from 'typescript';

const require = createRequire(import.meta.url);
function load(url) {
  const {outputText} = ts.transpileModule(readFileSync(url,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS}});
  const module = {exports:{}};
  new Function('require','module','exports',outputText)(name => {
    if (!name.startsWith('.')) return require(name);
    const file = ['', '.ts'].map(ext => new URL(name + ext, url)).find(existsSync);
    return load(file);
  }, module, module.exports);
  return module.exports;
}
const worker = load(new URL('../src/dev-worker.ts', import.meta.url));
const releases = load(new URL('../src/studio-releases.ts', import.meta.url));
const id = 'a'.repeat(32), scope = 'b'.repeat(64), commit = 'c'.repeat(40);
const response = state => ({schema:'OpenRemaster.DevWorkflowResult.v1',state,operation_id:id,production_go:false,independent_authority:false,engine:'unsigned-studio-dev-build',dev_receipt_verified:true});
function storage() {
  const values = new Map();
  return {getItem:key=>values.get(key)??null,setItem:(key,value)=>values.set(key,value),removeItem:key=>values.delete(key)};
}
function release(published='2026-11-18T07:51:39Z') {
  const tag = `studio-dev-${commit.slice(0,12)}-123-1`, name = `OpenRemaster-Studio-DEV-windows-x64-${commit.slice(0,12)}.zip`;
  return {draft:false,prerelease:true,tag_name:tag,target_commitish:commit,published_at:published,html_url:`${releases.repository}/releases/tag/${tag}`,body:'DEV release',assets:[{name,size:100,digest:`sha256:${'d'.repeat(64)}`,browser_download_url:`${releases.repository}/releases/download/${tag}/${name}`}]};
}
test('portable IPC cannot be mistaken for a commissioned worker', () => {
  const raw={schema:'OpenRemaster.StudioCapabilities.v1',production_go:false,worker_compiled:false,worker_ready:false,worker_scope:null,reason:'Portable UI'};
  assert.equal(worker.parseCapabilities(raw).worker_ready,false);
  assert.throws(()=>worker.parseCapabilities({...raw,worker_ready:true}));
  assert.throws(()=>worker.parseCapabilities({...raw,worker_compiled:true}));
});
test('legacy operation survives until a matching native observation is saved', () => {
  const store=storage();store.setItem(worker.legacyOperationKey,id);
  assert.equal(worker.readOperation(store,scope).operation,id);
  worker.saveOperation(store,scope,id,null);
  assert.equal(store.getItem(worker.legacyOperationKey),id);
  worker.saveOperation(store,scope,id,response('STARTED'));
  assert.equal(store.getItem(worker.legacyOperationKey),null);
  assert.equal(worker.readOperation(store,scope).result.state,'STARTED');
  assert.equal(worker.readOperation(store,'e'.repeat(64)),null);
});
test('corrupt durable state and storage failures cannot silently lose an operation', () => {
  const store=storage();store.setItem(worker.operationKey(scope),'{broken');
  assert.throws(()=>worker.readOperation(store,scope));
  assert.throws(()=>worker.saveOperation({setItem(){throw Error('quota');}},scope,id,null));
  for(const state of ['STARTED','HOLD','NOT_FOUND','REQUESTED']) assert.equal(worker.canStartAnother(response(state)),false);
});
test('mismatched, production, replay and oversized log responses are rejected', () => {
  const raw=response('STARTED');
  for(const change of [{operation_id:'f'.repeat(32)},{production_go:true},{independent_authority:true},{automatic_retry:true},{state:'PUBLISHED'},{logs:{'stdout.log':'x'.repeat(8193)}}]) {
    assert.throws(()=>worker.parseDevResult(JSON.stringify({...raw,...change}),id));
  }
  assert.equal(worker.parseDevResult(JSON.stringify({...raw,logs:{'stdout.log':'compiling'}}),id).logs['stdout.log'],'compiling');
  assert.throws(()=>worker.parseDevResult(JSON.stringify(response('COMMITTED')),id));
});

test('BUSY and DENIED status observations never authorize a new submission', () => {
  for (const state of ['BUSY','DENIED']) {
    for (const count of [undefined,0,1]) {
      const value=worker.parseDevResult(JSON.stringify({...response(state),launch_count:count}),id);
      assert.equal(value.launch_count,count);
      assert.equal(worker.canStartAnother(value),false);
    }
  }
});

test('durable operation metadata omits transient logs and refuses oversized writes', () => {
  const store=storage();
  worker.saveOperation(store,scope,id,{...response('STARTED'),logs:{'stdout.log':'x'.repeat(8192)}});
  assert.equal(worker.readOperation(store,scope).result.logs,undefined);
  const saved=store.getItem(worker.operationKey(scope));
  assert.throws(()=>worker.saveOperation(store,scope,id,{...response('STARTED'),extra:'x'.repeat(131072)}),/too large/);
  assert.equal(store.getItem(worker.operationKey(scope)),saved);
});
test('release selection uses publication time and retains old tag support', () => {
  const older=release('2026-11-17T07:51:39Z');older.tag_name=`studio-dev-${commit}`;older.html_url=`${releases.repository}/releases/tag/${older.tag_name}`;
  older.assets[0].browser_download_url=`${releases.repository}/releases/download/${older.tag_name}/${older.assets[0].name}`;
  const parsed=releases.parseStudioReleases([older,release()]);
  assert.equal(parsed[0].published,'2026-11-18T07:51:39Z');
  assert.equal(parsed[1].tag,older.tag_name);
});
test('release URLs, source revisions and CI observations are bound to this repository', () => {
  for(const change of [{target_commitish:'main'},{html_url:'https://evil.example/releases'},{tag_name:'studio-dev-../../evil'}]) assert.throws(()=>releases.parseStudioReleases([{...release(),...change}]));
  const bad=release();bad.assets[0].browser_download_url='https://evil.example/setup.exe';
  assert.throws(()=>releases.parseStudioReleases([bad]));
  const selected=releases.parseStudioReleases([release()])[0];
  const ci={id:123,head_sha:commit,event:'push',path:'.github/workflows/studio-windows-dev.yml',status:'completed',conclusion:'success'};
  assert.match(releases.parseReleaseCi(ci,selected),/CI passed/);
  assert.throws(()=>releases.parseReleaseCi({...ci,head_sha:'e'.repeat(40)},selected));
});
test('download verification compares actual file bytes with the selected release digest', async () => {
  const bytes=Buffer.from('DEV ZIP fixture'),digest=createHash('sha256').update(bytes).digest('hex');
  assert.equal(await releases.verifyReleaseFile(new File([bytes],'preview.zip'),digest),digest);
  await assert.rejects(()=>releases.verifyReleaseFile(new File(['altered'],'preview.zip'),digest),/mismatch/);
  await assert.rejects(()=>releases.verifyReleaseFile(new File([],'empty.zip'),digest));
});
