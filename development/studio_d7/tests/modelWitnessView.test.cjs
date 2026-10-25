const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {createRequire}=require('node:module');
const deps=process.env.STUDIO_NODE_MODULES || path.resolve(__dirname,'../node_modules');
const dependency=createRequire(path.join(deps,'../package.json'));
const ts=dependency('typescript');
const src=process.env.STUDIO_CANDIDATE_SOURCE || path.resolve(__dirname,'../src');
function load(name,overrides={}) {
  const source=fs.readFileSync(path.join(src,name),'utf8');
  const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}}).outputText;
  const m={exports:{}};
  new Function('require','module','exports',output)(id=>Object.hasOwn(overrides,id)?overrides[id]:dependency(id),m,m.exports);
  return m.exports;
}
const {modelWitnessView}=load('modelWitnessView.ts');
const Panel=load('MasterDevelopmentPanel.tsx',{'./modelWitnessView':{modelWitnessView}}).default;
const React=dependency('react');const {renderToStaticMarkup}=dependency('react-dom/server');
function fixture(){
  const context={project:'SYNTHETIC',proposalDigest:'a'.repeat(64),modelDigest:'b'.repeat(64),sourceManifestDigest:'c'.repeat(64),witnessDigest:'d'.repeat(64)};
  const observation={schema:'OpenRemaster.RLR.ModelWitnessResult.v1',status:'STATIC_CANDIDATE',scope:'SUPPLIED_DECLARATIVE_MODEL_ONLY',project:context.project,model_digest:context.modelDigest,source_manifest_digest:context.sourceManifestDigest,witness_digest:context.witnessDigest,initial_state:'e'.repeat(64),final_state:'f'.repeat(64),ending_id:'fixture-ending',steps_checked:3,original_game_validated:false,native_roundtrip_verified:false,may_dispatch:false,may_release:false,may_sign:false,may_publish:false,may_promote:false,may_fallback:false};
  const advisory={schema:'OpenRemaster.MasterAdvisoryPackage.v1',project:context.project,proposal_digest:context.proposalDigest,status:'HOLD_ADMISSION_REQUIRED',executor:'EXISTING_K003_ONLY',may_dispatch:false,may_acquire_lease:false,may_sign:false,may_publish:false,production_go:false,resource_request:{heavy_slots:0,max_global_heavy_slots:3},required_authorities:['PROJECT_OWNER','WRITER_LEASE','K003','RESOURCE_GOVERNOR'],model_witness_observation:observation};
  return {context,advisory,observation};
}
test('default panel has no model evidence or operational action',()=>{
  const html=renderToStaticMarkup(React.createElement(Panel));
  assert.match(html,/No model path evidence supplied/);assert.doesNotMatch(html,/<button|<form|<script/);
});
test('matching report remains model only and production hold',()=>{
  const {context,advisory}=fixture();const v=modelWitnessView(advisory,context);
  assert.equal(v.state,'recorded');assert.equal(v.steps,3);assert.match(v.detail,/Production on hold/);
  const html=renderToStaticMarkup(React.createElement(Panel,{advisory,evidenceContext:context}));
  assert.match(html,/Reported model path check/);assert.match(html,/does not independently verify/);
  assert.match(html,/<summary>Developer Mode · Model evidence references/);assert.doesNotMatch(html,/<button|<form/);
});
test('missing context or observation holds',()=>{
  const {context,advisory}=fixture();assert.equal(modelWitnessView(advisory).state,'hold');
  delete advisory.model_witness_observation;assert.equal(modelWitnessView(advisory,context).state,'hold');
});
test('every identity mismatch holds without references',()=>{
  for(const key of ['project','proposalDigest','modelDigest','sourceManifestDigest','witnessDigest']){
    const {context,advisory}=fixture();context[key]=key==='project'?'FOREIGN':'0'.repeat(64);
    const v=modelWitnessView(advisory,context);assert.equal(v.state,'hold',key);assert.deepEqual(v.references,[]);
  }
});
test('all authority flags must be explicitly false',()=>{
  for(const nested of [false,true]){
    const baseline=fixture();const keys=Object.keys(nested?baseline.observation:baseline.advisory).filter(k=>k.startsWith('may_')||['production_go','original_game_validated','native_roundtrip_verified'].includes(k));
    for(const key of keys)for(const bad of [true,0,'false',undefined]){
      const {context,advisory,observation}=fixture();(nested?observation:advisory)[key]=bad;
      assert.equal(modelWitnessView(advisory,context).state,'hold',key);
    }
  }
});
test('unknown positive capabilities hold',()=>{
  const {context,advisory,observation}=fixture();observation.may_execute=true;
  assert.equal(modelWitnessView(advisory,context).state,'hold');delete observation.may_execute;
  advisory.may_fallback=true;assert.equal(modelWitnessView(advisory,context).state,'hold');
});
test('wrong schema scope status executor and resources hold',()=>{
  for(const [target,key,value] of [['o','schema','unknown'],['o','scope','RUNTIME'],['o','status','VERIFIED'],['a','executor','NEW_SCHEDULER'],['a','status','READY'],['a','schema','unknown'],['a','required_authorities',[]],['a','resource_request',{heavy_slots:1,max_global_heavy_slots:3}]]){
    const {context,advisory,observation}=fixture();(target==='a'?advisory:observation)[key]=value;
    assert.equal(modelWitnessView(advisory,context).state,'hold',key);
  }
});
test('step counts are bounded integers',()=>{
  for(const value of [-1,1025,NaN,Infinity,1.5,true,'3']){
    const {context,advisory,observation}=fixture();observation.steps_checked=value;
    assert.equal(modelWitnessView(advisory,context).state,'hold');
  }
  const {context,advisory,observation}=fixture();observation.steps_checked=0;
  assert.equal(modelWitnessView(advisory,context).state,'recorded');
});
test('malformed states and context hashes hold',()=>{
  const {context,advisory,observation}=fixture();observation.final_state='invalid';
  assert.equal(modelWitnessView(advisory,context).state,'hold');observation.final_state='f'.repeat(64);
  context.modelDigest='B'.repeat(64);assert.equal(modelWitnessView(advisory,context).state,'hold');
});
test('untrusted labels are escaped by React',()=>{
  const {context,advisory,observation}=fixture();context.project='<script>alert(1)</script>';advisory.project=context.project;observation.project=context.project;
  observation.ending_id='<img src=x onerror=alert(1)>';
  const html=renderToStaticMarkup(React.createElement(Panel,{advisory,evidenceContext:context}));
  assert.doesNotMatch(html,/<script|<img/);assert.match(html,/&lt;script&gt;/);assert.match(html,/&lt;img/);
});
test('inputs stay unchanged and output references are detached',()=>{
  const f=fixture();const before=JSON.stringify(f);const v=modelWitnessView(f.advisory,f.context);
  v.references[0][1]='changed';assert.equal(JSON.stringify(f),before);
});
test('malformed values fail closed without throwing',()=>{
  for(const a of [false,true,0,'PASS',[],{}, {model_witness_observation:[]}])assert.equal(modelWitnessView(a,fixture().context).state,'hold');
});
