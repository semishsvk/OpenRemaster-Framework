import {createRequire} from 'node:module';
import {readFileSync,lstatSync,realpathSync,readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve,relative,sep,isAbsolute} from 'node:path';
export const projectRoot=fileURLToPath(new URL('../../',import.meta.url));
export const dependencyRoot=resolve(projectRoot,'.studio-test-deps');
const root=resolve(dependencyRoot,'node_modules'),req=createRequire(resolve(dependencyRoot,'package.json'));
const names=new Set(['typescript','react','react/jsx-runtime','react-dom/server']);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const manifestRaw=readFileSync(new URL('../../OFFLINE-DEPENDENCIES.json',import.meta.url));
if(digest(manifestRaw)!=='ba265c7b238cc1b04bae8193e264c77690ff76e8a42df50f8192ed2dc9197356')throw Error('LOCAL_DEPS_MANIFEST_PIN');
const manifest=JSON.parse(manifestRaw),expected=new Map(),dirs=new Set(['node_modules']);
for(const item of manifest.files){
 if(typeof item.path!=='string'||!item.path.startsWith('node_modules/')||item.path.split('/').some(x=>!x||x==='..'||x==='.')||expected.has(item.path))throw Error('LOCAL_DEPS_MANIFEST');
 expected.set(item.path,item);
 const parts=item.path.split('/');for(let i=1;i<parts.length;i++)dirs.add(parts.slice(0,i).join('/'));
}
const localRelative=path=>relative(dependencyRoot,path).split(sep).join('/');
function inside(path){const rel=relative(root,path);return rel!==''&&rel!=='..'&&!rel.startsWith('..'+sep)&&!isAbsolute(rel);}
let checked=false;
export function validateDependencies(){
 if(checked)return;
 let stat;try{stat=lstatSync(dependencyRoot);}catch{throw Error('LOCAL_DEPS_UNAVAILABLE');}
 if(!stat.isDirectory()||stat.isSymbolicLink()||realpathSync(dependencyRoot)!==dependencyRoot)throw Error('LOCAL_DEPS_PATH');
 const foundFiles=new Set(),foundDirs=new Set();
 function walk(path){
  let info;try{info=lstatSync(path);}catch{throw Error('LOCAL_DEPS_UNAVAILABLE');}
  const rel=localRelative(path);
  if(info.isSymbolicLink()||realpathSync(path)!==path)throw Error('LOCAL_DEPS_PATH');
  if(info.isDirectory()){
   if(!dirs.has(rel))throw Error('LOCAL_DEPS_EXTRA '+rel);foundDirs.add(rel);
   for(const name of readdirSync(path))walk(resolve(path,name));
  }else if(info.isFile()){
   if(!expected.has(rel))throw Error('LOCAL_DEPS_EXTRA '+rel);foundFiles.add(rel);
  }else throw Error('LOCAL_DEPS_PATH');
 }
 walk(root);
 if(foundFiles.size!==expected.size||foundDirs.size!==dirs.size)throw Error('LOCAL_DEPS_UNAVAILABLE');
 for(const [rel,item]of expected){
  const raw=readFileSync(resolve(dependencyRoot,rel));
  if(raw.length!==item.bytes||digest(raw)!==item.sha256)throw Error('LOCAL_DEPS_CHANGED '+rel);
 }
 checked=true;
}
export function assertDependencyFile(path){
 const actual=realpathSync(path);
 if(!inside(actual)||!expected.has(localRelative(actual)))throw Error('LOCAL_DEPS_OUTSIDE_PROJECT');
}
export function dependency(name){
 if(!names.has(name))throw Error('LOCAL_DEPS_SPECIFIER');
 validateDependencies();
 let target;try{target=req.resolve(name);}catch{throw Error('LOCAL_DEPS_UNAVAILABLE '+name);}
 assertDependencyFile(target);
 const value=req(name);
 for(const loaded of Object.keys(req.cache))assertDependencyFile(loaded);
 return value;
}
