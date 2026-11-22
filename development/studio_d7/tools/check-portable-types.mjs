import {dependency,projectRoot as root,dependencyRoot,assertDependencyFile} from '../tests/support/local-dependencies.mjs';
import {resolve,relative,isAbsolute,sep,basename} from 'node:path';
import {readFileSync,realpathSync} from 'node:fs';
import {createHash} from 'node:crypto';
const ts=dependency('typescript'),types=resolve(dependencyRoot,'node_modules/@types');
const config=ts.readConfigFile(resolve(root,'tsconfig.json'),ts.sys.readFile);
if(config.error)throw Error(ts.flattenDiagnosticMessageText(config.error.messageText,'\n'));
const parsed=ts.parseJsonConfigFileContent(config.config,ts.sys,root);
if(parsed.errors.length)throw Error('TSC_CONFIG');
const options={...parsed.options,baseUrl:root,typeRoots:[types],types:['react','react-dom'],paths:{react:[resolve(types,'react/index.d.ts')],'react/*':[resolve(types,'react/*')],'react-dom':[resolve(types,'react-dom/index.d.ts')],'react-dom/*':[resolve(types,'react-dom/*')],csstype:[resolve(dependencyRoot,'node_modules/csstype/index.d.ts')]}};
const files=parsed.fileNames.filter(f=>basename(f)!=='vite.config.ts');
const program=ts.createProgram(files,options);
for(const file of program.getSourceFiles()){
 const rel=relative(resolve(root,'src'),file.fileName);
 if(rel!==''&&rel!=='..'&&!rel.startsWith('..'+sep)&&!isAbsolute(rel))continue;
 const notice=resolve(root,'evidence/NODE_v24.19.0_WINDOWS_SIGNATURE.json');
 if(resolve(file.fileName)===notice&&realpathSync(notice)===notice&&createHash('sha256').update(readFileSync(notice)).digest('hex')==='58f7383ce36b6b2d96b0de3a7d01d770eb70ead3e00b8c38f925512da917b7f9')continue;
 try{assertDependencyFile(file.fileName);}catch{throw Error('TYPE_SOURCE_OUTSIDE '+file.fileName);}
}
const diagnostics=ts.getPreEmitDiagnostics(program);
if(diagnostics.length){console.error(ts.formatDiagnosticsWithColorAndContext(diagnostics,{getCanonicalFileName:x=>x,getCurrentDirectory:()=>root,getNewLine:()=> '\n'}));process.exitCode=1;}
else console.log(JSON.stringify({state:'PASS_FENCED_PROJECT_UI_TYPES',files:files.length,program_source_files:program.getSourceFiles().length,source_roots:[resolve(root,'src'),dependencyRoot],additional_pinned_project_input:'evidence/NODE_v24.19.0_WINDOWS_SIGNATURE.json',automatic_ancestor_types:false,native_compile:false}));
