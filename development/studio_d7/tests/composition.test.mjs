import assert from 'node:assert/strict';
import test from 'node:test';
import {existsSync,readFileSync} from 'node:fs';
import {dependency as baseline} from './support/local-dependencies.mjs';
import {binding,now} from './project-fixture.mjs';
const ts=baseline('typescript'),React=baseline('react'),{renderToStaticMarkup}=baseline('react-dom/server');
const root=new URL('../',import.meta.url),cache=new Map();
function load(url){
 if(cache.has(url.href))return cache.get(url.href);
 const module={exports:{}};cache.set(url.href,module.exports);
 const code=ts.transpileModule(readFileSync(url,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 new Function('require','module','exports',code)(name=>{
  if(!name.startsWith('.'))return baseline(name);
  const dest=['.ts','.tsx'].map(ext=>new URL(name+ext,url)).find(p=>existsSync(p));
  assert.ok(dest,'relative source module must exist: '+name);return load(dest);
 },module,module.exports);cache.set(url.href,module.exports);return module.exports;
}
const {readNativeFileObservation:read}=load(new URL('src/native-file-transport.ts',root));
const {parseNativeFileObservation:parse,observationProjectInput:project}=load(new URL('src/native-file-observation.ts',root));
const {ProjectWorkspace}=load(new URL('src/ProjectWorkspace.tsx',root));
function native(invoke,body){const old=Object.getOwnPropertyDescriptor(globalThis,'window');globalThis.window={__TAURI_INTERNALS__:{invoke}};return Promise.resolve().then(body).finally(()=>{if(old)Object.defineProperty(globalThis,'window',old);else delete globalThis.window;});}

test('actual App source supplies fixed reader and no independently unaccepted binding',()=>{
 const ast=ts.createSourceFile('App.tsx',readFileSync(new URL('src/App.tsx',root),'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
 const nodes=[];function visit(n){if(ts.isJsxSelfClosingElement(n)&&n.tagName.getText(ast)==='ProjectWorkspace')nodes.push(n);ts.forEachChild(n,visit);}visit(ast);
 assert.equal(nodes.length,1);const attrs=nodes[0].attributes.properties;
 assert.equal(attrs.length,1);assert.equal(attrs[0].name.text,'read');assert.equal(attrs[0].initializer.expression.getText(ast),'readNativeFileObservation');
 const imp=ast.statements.find(n=>ts.isImportDeclaration(n)&&n.moduleSpecifier.text==='./native-file-transport');
 assert.ok(imp?.importClause.namedBindings.elements.some(n=>n.name.text==='readNativeFileObservation'));
});
test('fixed reader plus strict consumer converts simulated empty-catalog native HOLD to no physical project',async()=>{
 const b=binding(),calls=[];
 const hold={schema:'OpenRemaster.NativeFileObservation.v1',state:'HOLD',reason:'NO_ACCEPTED_SELECTION',read_only:true,execution_authority:false,gameplay:'UNKNOWN',fidelity:'UNKNOWN',observed_epoch_ms:now};
 await native(async(...args)=>{calls.push(args);return hold;},async()=>{
  const raw=await read(b.request);assert.equal(project(parse(raw,b,now),b,now),null);
 });
 assert.deepEqual(calls,[['local_dev_file_observation',{selection:b.request}]]);
});
test('whole renderer transport-consumer path still rejects a forged authority response',async()=>{
 const b=binding();await native(async()=>({schema:'OpenRemaster.NativeFileObservation.v1',state:'HOLD',reason:'NO_ACCEPTED_SELECTION',read_only:true,execution_authority:true,gameplay:'UNKNOWN',fidelity:'UNKNOWN',observed_epoch_ms:now}),async()=>{
  const raw=await read(b.request);assert.throws(()=>parse(raw,b,now));
 });
});
test('composed Workspace SSR with actual wired reader and no binding stays HOLD without invoking',async()=>{
 let calls=0;await native(async()=>{calls++;throw Error('no native calls allowed');},()=>{
  const html=renderToStaticMarkup(React.createElement(ProjectWorkspace,{read}));
  assert.match(html,/>HOLD</);assert.match(html,/No project and edition selection has been verified/);assert.match(html,/UNVERIFIED/);assert.equal(calls,0);
 });
});
test('fixed command is source-registered in both feature branches with typed selection and pinned child route',()=>{
 const main=readFileSync(new URL('src-tauri/src/main.rs',root),'utf8');
 const handlers=[...main.matchAll(/tauri::generate_handler!\[([\s\S]*?)\]/g)];assert.equal(handlers.length,2);
 for(const h of handlers)assert.equal(h[1].split(',').filter(x=>x.trim()==='local_dev_file_observation').length,1);
 assert.match(main,/async fn local_dev_file_observation\(selection: file_observation::Selection\)/);
 assert.match(main,/file_observation::observe\(selection\)/);
 const source=readFileSync(new URL('src-tauri/src/file_observation.rs',root),'utf8');
 assert.match(source,/root\.join\("r8-observation"\)\.join\("entry.py"\)/);
 assert.match(source,/\["-B","-I","-S","-c",&bootstrap\]/);
 assert.match(source,/call_python_output\(&config/);
});
