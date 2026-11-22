import {mkdirSync,mkdtempSync,readdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const cohort=process.argv.length===4&&process.argv[2]==='--cohort'&&process.argv[3]==='ups';
if(process.argv.length!==2&&!cohort)throw Error('SOURCE_TEST_ARGS');
const runs=resolve(root,'test-results');mkdirSync(runs,{recursive:true});
const out=mkdtempSync(resolve(runs,'source-')),temp=resolve(out,'private-temp');mkdirSync(temp);
const env={...process.env,TEMP:temp,TMP:temp,TMPDIR:temp};
for(const key of Object.keys(env))if(key.toUpperCase().startsWith('NODE_')||['STUDIO_TYPESCRIPT','STUDIO_NODE_MODULES'].includes(key.toUpperCase()))delete env[key];
// Preserve package.json's original tests/*.test.mjs selection, but add the guard.
const upsNames=['composition','native-file-observation','native-file-transport','project-input','project-workspace','studio-layout-coupling','unified-project-state'].map(name=>name+'.test.mjs');
const tests=readdirSync(resolve(root,'tests')).filter(name=>name.endsWith('.test.mjs')&&(!cohort||upsNames.includes(name))).sort().map(name=>resolve(root,'tests',name));
if(cohort&&tests.length!==upsNames.length)throw Error('SOURCE_COHORT_MISSING');
if(!tests.length)throw Error('SOURCE_TEST_SELECTION');
for(const [name,args]of [['inputs',[resolve(root,'tools/validate-test-inputs.mjs')]],['tests',['--import',new URL('./guard-test-temp.mjs',import.meta.url).href,'--test','--test-reporter=tap',...tests]],['types',[resolve(root,'tools/check-portable-types.mjs')]]]){
 const result=spawnSync(process.execPath,args,{cwd:root,env,timeout:45000,maxBuffer:2*1024*1024,encoding:'utf8',windowsHide:true});
 for(const stream of ['stdout','stderr'])writeFileSync(resolve(out,name+'.'+stream),result[stream]??'',{flag:'wx'});
 process.stdout.write(result.stdout??'');process.stderr.write(result.stderr??'');
 if(result.status!==0){console.error(JSON.stringify({state:'SOURCE_CHECKS_FAIL',phase:name,out,error:result.error?.message??null}));process.exit(result.status??1);}
}
console.log(JSON.stringify({state:'PASS_GUARDED_SOURCE_CHECKS',out,test_files:tests.length,cohort:cohort?'ups':'existing-test-glob',private_temp:true,native:false}));
