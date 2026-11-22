/** Exact local input provisioning only. No npm, network, compiler or fallback. */
import {createHash,randomUUID} from 'node:crypto';
import {existsSync,lstatSync,mkdirSync,readFileSync,readdirSync,realpathSync,renameSync,writeFileSync} from 'node:fs';
import {dirname,isAbsolute,relative,resolve,sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateDependencies} from '../tests/support/local-dependencies.mjs';

const project=fileURLToPath(new URL('../',import.meta.url));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const need=(condition,code)=>{if(!condition)throw Error(code);};
need(process.argv.length===4&&process.argv[2]==='--source','OFFLINE_SOURCE_ARGS');
const source=resolve(process.argv[3]),pool=resolve(project,'.studio-test-deps');
const raw=readFileSync(new URL('../OFFLINE-DEPENDENCIES.json',import.meta.url));
need(sha(raw)==='ba265c7b238cc1b04bae8193e264c77690ff76e8a42df50f8192ed2dc9197356','OFFLINE_MANIFEST_PIN');
const manifest=JSON.parse(raw);
const parentRaw=readFileSync(new URL('./offline-dependencies-parent.json',import.meta.url));
need(sha(parentRaw)==='033dcfc1596618fd0bfe80bcba10625c795a10ca51666a65cfb088d78c28aa24','OFFLINE_PARENT_PIN');
const parent=new Map(JSON.parse(parentRaw).files.map(row=>[row.path,row]));
const expected=new Map(),dirs=new Set();
for(const row of manifest.files){
 const original=parent.get('source/studio/'+row.path);
 need(original&&original.sha256===row.sha256&&original.bytes===row.bytes,'OFFLINE_PARENT_BINDING');
 need(row.path.startsWith('node_modules/')&&!expected.has(row.path),'OFFLINE_MANIFEST_PATH');
 expected.set(row.path,row);
 const parts=row.path.split('/');for(let i=1;i<parts.length;i++)dirs.add(parts.slice(0,i).join('/'));
}
need(expected.size===255,'OFFLINE_FILE_COUNT');
need(!source.startsWith(pool+sep)&&source!==pool,'OFFLINE_SOURCE_DESTINATION_ALIAS');
function canonicalDirectory(path){
 let info;try{info=lstatSync(path);}catch{throw Error('OFFLINE_SOURCE_MISSING');}
 need(info.isDirectory()&&!info.isSymbolicLink()&&realpathSync(path)===path,'OFFLINE_SOURCE_REPARSE');
}
for(let path=source;;path=dirname(path)){
 canonicalDirectory(path);if(dirname(path)===path)break;
}
const found=new Map();
function walk(path,rel){
 let stat;try{stat=lstatSync(path);}catch{throw Error('OFFLINE_SOURCE_MISSING '+rel);}
 need(!stat.isSymbolicLink()&&realpathSync(path)===path,'OFFLINE_SOURCE_REPARSE '+rel);
 if(stat.isDirectory()){
  need(dirs.has(rel),'OFFLINE_SOURCE_EXTRA '+rel);
  for(const name of readdirSync(path))walk(resolve(path,name),rel+'/'+name);
 }else{
  need(stat.isFile()&&expected.has(rel),'OFFLINE_SOURCE_EXTRA '+rel);
  const bytes=readFileSync(path),pin=expected.get(rel);
  need(bytes.length===pin.bytes&&sha(bytes)===pin.sha256,'OFFLINE_SOURCE_CHANGED '+rel);
  found.set(rel,bytes);
 }
}
// Other packages in an existing common-CI node_modules tree are outside this
// pool's declared input. Each of these seven complete packages is exact.
for(const name of manifest.packages)walk(resolve(source,name),'node_modules/'+name);
need(found.size===expected.size,'OFFLINE_SOURCE_MISSING');
let state;
if(existsSync(pool)){
 validateDependencies();state='REUSED_VERIFIED_EXACT_POOL';
}else{
 const staging=resolve(project,'.studio-test-deps.provision-'+randomUUID());
 mkdirSync(staging);
 for(const [rel,bytes]of found){
  const path=resolve(staging,rel),part=relative(staging,path);
  need(!isAbsolute(part)&&part!=='..'&&!part.startsWith('..'+sep),'OFFLINE_OUTPUT_PATH');
  mkdirSync(dirname(path),{recursive:true});writeFileSync(path,bytes,{flag:'wx'});
 }
 // No overwrite/retry or automatic deletion on an ambiguous failure.
 renameSync(staging,pool);validateDependencies();state='PROVISIONED_VERIFIED_EXACT_POOL';
}
console.log(JSON.stringify({state,source,pool,files:found.size,bytes:[...found.values()].reduce((n,b)=>n+b.length,0),parent_manifest_sha256:sha(parentRaw),network:false,install:false,execution_authority:false}));
