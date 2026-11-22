import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {dependency as baseline} from './support/local-dependencies.mjs';
import {binding} from './project-fixture.mjs';
const ts=baseline('typescript'), React=baseline('react'), {renderToStaticMarkup}=baseline('react-dom/server');
const cache=new Map();
function load(url) {
  if(cache.has(url.href))return cache.get(url.href);
  const {outputText}=ts.transpileModule(readFileSync(url,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}});
  const module={exports:{}};
  new Function('require','module','exports',outputText)(name=>name.startsWith('.')?load(new URL(name+'.ts',url)):baseline(name),module,module.exports);
  cache.set(url.href,module.exports);return module.exports;
}
const {ProjectWorkspace}=load(new URL('../src/ProjectWorkspace.tsx',import.meta.url));
test('default unbound native adapter stays HOLD and unverified',()=>{
  const html=renderToStaticMarkup(React.createElement(ProjectWorkspace));
  assert.match(html,/>HOLD</);assert.match(html,/accepted catalog and producer contract/);assert.match(html,/UNVERIFIED/);
  assert.doesNotMatch(html,/>PASS</);assert.doesNotMatch(html,/<button/);assert.match(html,/issues no execution permission/);
});
test('malformed catalog selection is rejected without reader or authority',()=>{
  const b=binding();b.request.project_id='<script>bad</script>';
  const html=renderToStaticMarkup(React.createElement(ProjectWorkspace,{binding:b}));
  assert.doesNotMatch(html,/<script>/);assert.match(html,/>HOLD</);assert.match(html,/UNKNOWN/);
});
test('rendering never invokes a native reader or fabricates a current build',()=>{
  let called=0;
  const html=renderToStaticMarkup(React.createElement(ProjectWorkspace,{binding:binding(),read:async()=>{called++;throw Error('not a real adapter');}}));
  assert.equal(called,0);assert.match(html,/>UNKNOWN</);assert.match(html,/UNVERIFIED/);
});
