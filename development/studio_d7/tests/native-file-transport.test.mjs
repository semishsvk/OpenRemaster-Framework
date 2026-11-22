import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {dependency as baseline} from './support/local-dependencies.mjs';
const ts=baseline('typescript');
const src=readFileSync(new URL('../src/native-file-transport.ts',import.meta.url),'utf8');
const module={exports:{}};
new Function('module','exports',ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText)(module,module.exports);
const {invokeFileObservation:invoke,readNativeFileObservation:read}=module.exports;
const selection=()=>({project_id:'Fixture',edition_id:'DEV',committed_operation_id:'a'.repeat(32),accepted_manifest_digest:'b'.repeat(64)});
test('fixed command passes only copied four-key selection and treats response as unknown',async()=>{
  const s=selection(),raw={state:'invented'},calls=[];
  assert.equal(await invoke(s,async(...args)=>{calls.push(args);s.project_id='Changed';return raw;}),raw);
  assert.deepEqual(calls,[['local_dev_file_observation',{selection:selection()}]]);
  assert.ok(Object.isFrozen(calls[0][1].selection));
});
for(const [label,mutate] of [
  ['path key',s=>s.path='C:/secret.exe'],['command key',s=>s.command='other'],
  ['traversal project',s=>s.project_id='../x'],['missing edition',s=>delete s.edition_id],
  ['long project',s=>s.project_id='a'.repeat(65)],['uppercase operation',s=>s.committed_operation_id='A'.repeat(32)],
  ['invalid digest',s=>s.accepted_manifest_digest='x'.repeat(64)],
  ['accessor',s=>Object.defineProperty(s,'edition_id',{get(){throw Error('getter must not run');},enumerable:true})],
  ['symbol field',s=>s[Symbol('x')]=1],['custom prototype',s=>Object.setPrototypeOf(s,{})]
]) test('reject '+label+' without invoking native',async()=>{
  const s=selection();mutate(s);let calls=0;
  await assert.rejects(invoke(s,async()=>{calls++;}));assert.equal(calls,0);
});
test('transport rejection propagates so Workspace drops previous response',async()=>{
  await assert.rejects(invoke(selection(),async()=>{throw Error('unavailable');}),/unavailable/);
});
test('no desktop bridge in SSR fails without execution or fallback',async()=>{
  assert.equal(typeof window,'undefined');await assert.rejects(read(selection()),/NATIVE_OBSERVATION_UNAVAILABLE/);
});
