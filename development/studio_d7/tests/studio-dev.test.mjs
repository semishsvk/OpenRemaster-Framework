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
const diagnostics = load(new URL('../src/dev-diagnostics.ts', import.meta.url));
const releases = load(new URL('../src/studio-releases.ts', import.meta.url));
const id = 'a'.repeat(32), scope = 'b'.repeat(64), commit = 'c'.repeat(40);
test('diagnostics expire and unknown authority never enables a build',()=>{
  const report={schema:'OpenRemaster.DevPreflight.v1',scope,production_go:false,checked_at_ms:1000,valid_for_ms:30000,can_submit:true,
    checks:diagnostics.diagnosticIds.map(id=>({id,status:'PASS',detail:'Verified fixture',next_step:'Review fixture'}))};
  const parsed=diagnostics.parsePreflight(report,scope);
  assert.equal(diagnostics.preflightAllowsSubmit(parsed,1000),true);
  assert.equal(diagnostics.preflightAllowsSubmit(parsed,31000),false);
  assert.equal(diagnostics.preflightAllowsSubmit(parsed,999),false);
  const unknown={...report,checks:report.checks.map(row=>row.id==='owner'?{...row,status:'UNKNOWN'}:row)};
  assert.throws(()=>diagnostics.parsePreflight(unknown,scope));
  assert.equal(diagnostics.preflightAllowsSubmit(diagnostics.parsePreflight({...unknown,can_submit:false},scope),1000),false);
  assert.throws(()=>diagnostics.parsePreflight({...report,checks:report.checks.slice(1)},scope));
  assert.throws(()=>diagnostics.parsePreflight(report,'e'.repeat(64)));
});
test('a not-admitted proof releases only its matching saved attempt after explicit acknowledgment',()=>{
  const attempt='d'.repeat(32),hash='e'.repeat(64);
  const raw={...response('DENIED'),schema:'OpenRemaster.DevWorkflowResult.v2',control_scope:scope,control_verified:true,dev_receipt_verified:false,
    evidence_sha256:hash,launch_count:0,recovery:{allowed:true,reason:'No intent, queue or ledger exists'},
    not_admitted:{schema:'OpenRemaster.NotAdmitted.v1',operation_id:id,scope,attempt_id:attempt,reason:'Native admission unavailable',record_sha256:hash,production_go:false},
    archive:{operation_id:id,evidence_sha256:hash,manifest_sha256:hash,path:'C:/DEV/archive',log_count:0,retention:'KEEP_UNTIL_EXPLICIT_EXPORT_AND_REVIEW'},
    resolution:{operation_id:id,scope,evidence_sha256:hash,archive_manifest_sha256:hash,record_sha256:hash,disposition:'ACKNOWLEDGED_NO_RETRY',reason:'Reviewed this fresh rejected attempt.',new_operation_allowed:true,production_go:false}};
  const parsed=worker.parseDevResult(JSON.stringify(raw),id,scope);
  assert.equal(worker.canStartAnother(parsed),false);
  assert.equal(worker.canStartAnother(parsed,'f'.repeat(32)),false);
  assert.equal(worker.canStartAnother(parsed,attempt),true);
  assert.equal(worker.canStartAnother({...parsed,resolution:null},attempt),false);
  const store=storage();worker.saveOperation(store,scope,id,null,attempt);worker.saveOperation(store,scope,id,parsed);
  assert.equal(worker.readOperation(store,scope).attempt_id,attempt);
  assert.throws(()=>worker.parseDevResult(JSON.stringify({...raw,launch_count:1}),id,scope));
});
test('log pages verify bytes, scope, progress and archive identity',async()=>{
  const bytes=Buffer.from('error: žltý fixture\r\nwarning: retained\n');
  const hash=createHash('sha256').update(bytes).digest('hex');
  const page={schema:'OpenRemaster.DevLogPage.v1',operation_id:id,scope,evidence_sha256:hash,source:'archive',name:'stdout.log',offset:0,next_offset:bytes.length,total_bytes:bytes.length,
    bytes_base64:bytes.toString('base64'),chunk_sha256:hash,file_sha256:hash,manifest_sha256:hash,verified:true,eof:true,production_go:false};
  const parse=value=>diagnostics.parseLogPage(JSON.stringify(value),id,scope,hash,'archive','stdout.log',0,hash);
  assert.deepEqual(Buffer.from((await parse(page)).bytes),bytes);
  await assert.rejects(()=>parse({...page,bytes_base64:Buffer.from('tampered').toString('base64')}));
  await assert.rejects(()=>parse({...page,scope:'f'.repeat(64)}));
  await assert.rejects(()=>parse({...page,manifest_sha256:'f'.repeat(64)}));
  await assert.rejects(()=>parse({...page,eof:false}));
  await assert.rejects(()=>parse({...page,verified:false}));
  assert.equal(diagnostics.filterLog(bytes.toString(),'fixture','error'),'error: žltý fixture');
  assert.match(diagnostics.filterLog(bytes.toString(),'','warning'),/^warning:/);
});
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

test('read-only worker observations require a verified control scope', () => {
  const raw={...response('QUEUED'),schema:'OpenRemaster.DevWorkflowResult.v2',control_scope:scope,control_verified:true,dev_receipt_verified:false,evidence_sha256:'d'.repeat(64),recovery:{allowed:false,reason:'Queued work cannot be resolved'},archive:null,resolution:null};
  assert.equal(worker.parseDevResult(JSON.stringify(raw),id,scope).state,'QUEUED');
  assert.equal(worker.parseDevResult(JSON.stringify({...raw,state:'RUNNING'}),id,scope).dev_receipt_verified,false);
  assert.throws(()=>worker.parseDevResult(JSON.stringify(raw),id));
  assert.throws(()=>worker.parseDevResult(JSON.stringify(raw),id,'e'.repeat(64)));
  assert.throws(()=>worker.parseDevResult(JSON.stringify({...raw,control_verified:false}),id,scope));
});

test('a resolved hold requires matching operation, snapshot, scope and archive evidence', () => {
  const archive={path:'C:/DEV/archive',operation_id:id,evidence_sha256:'d'.repeat(64),manifest_sha256:'e'.repeat(64),log_count:2,retention:'KEEP_UNTIL_EXPLICIT_EXPORT_AND_REVIEW'};
  const resolution={disposition:'ACKNOWLEDGED_NO_RETRY',operation_id:id,scope,evidence_sha256:archive.evidence_sha256,archive_manifest_sha256:archive.manifest_sha256,record_sha256:'f'.repeat(64),reason:'Reviewed a stopped owned build.',new_operation_allowed:true,production_go:false};
  const raw={...response('HOLD'),schema:'OpenRemaster.DevWorkflowResult.v2',control_scope:scope,control_verified:true,dev_receipt_verified:false,evidence_sha256:archive.evidence_sha256,recovery:{allowed:true,reason:'Stopped owned tree'},archive,resolution};
  const parsed=worker.parseDevResult(JSON.stringify(raw),id,scope);
  assert.equal(parsed.state,'HOLD');assert.equal(worker.canStartAnother(parsed),true);
  for(const change of [{scope:'1'.repeat(64)},{operation_id:'2'.repeat(32)},{evidence_sha256:'3'.repeat(64)},{archive_manifest_sha256:'4'.repeat(64)},{production_go:true}]) {
    assert.throws(()=>worker.parseDevResult(JSON.stringify({...raw,resolution:{...resolution,...change}}),id,scope));
  }
  assert.throws(()=>worker.parseDevResult(JSON.stringify({...raw,archive:null}),id,scope));
  const store=storage();worker.saveOperation(store,scope,id,parsed);
  assert.equal(worker.readOperation(store,scope).result.resolution.record_sha256,resolution.record_sha256);
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
