import type {ProjectInput} from './unified-project-state';
import {artifactPath, parseProjectInput} from './project-input';

export type ObservationRequest = Readonly<{project_id: string; edition_id: string; committed_operation_id: string; accepted_manifest_digest: string}>;
type ExpectedFile = Readonly<{role: 'EXE' | 'PCK'; name: string; sha256: string; bytes: number}>;
/** Supplied from an independently admitted catalog/manifest, never derived
 * from the response being checked. No real catalog is admitted in this source.
 */
export type ObservationBinding = Readonly<{
  request: ObservationRequest; engine: string; sourceCommit: string; sourceTree: string;
  sourceManifestSha256: string; buildPlanSha256: string; requiresPck: boolean;
  files: readonly ExpectedFile[];
}>;
type FileObservation = ExpectedFile & Readonly<{volume: string; file_id: string}>;
type Common = Readonly<{schema: 'OpenRemaster.NativeFileObservation.v1'; read_only: true; execution_authority: false;
  gameplay: 'UNKNOWN'; fidelity: 'UNKNOWN'; observed_epoch_ms: number}>;
export type NativeFileObservation = Common & (
  Readonly<{state: 'HOLD'; reason: 'NO_ACCEPTED_SELECTION' | 'INVALID_REQUEST' | 'UNVERIFIED'}> |
  Readonly<{state: 'LIVE'; selection: ObservationRequest; engine: string; source_commit: string; source_tree: string;
    source_manifest_sha256: string; build_plan_sha256: string; files: readonly FileObservation[]}>
);
const TTL = 5_000, MAX_ARTIFACT_BYTES = 256 * 1024 * 1024;
type Obj = Record<string, unknown>;
const hex = (v: unknown, n: number): v is string => typeof v === 'string' && new RegExp('^[a-f0-9]{'+n+'}$').test(v);
const id = (v: unknown): v is string => typeof v === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(v);
function need(v: unknown): asserts v { if (!v) throw Error('NATIVE_FILE_OBSERVATION_INVALID'); }
function object(v: unknown, keys: readonly string[]): Obj {
  need(v !== null && typeof v === 'object' && !Array.isArray(v));
  need(Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null);
  const own = Reflect.ownKeys(v); need(own.length === keys.length && own.every(k => typeof k === 'string' && keys.includes(k)));
  for (const key of keys) need(Object.getOwnPropertyDescriptor(v, key)?.value !== undefined);
  return v as Obj;
}
function list(v: unknown): unknown[] {
  need(Array.isArray(v) && Object.getPrototypeOf(v) === Array.prototype && v.length >= 1 && v.length <= 2);
  need(Reflect.ownKeys(v).length === v.length + 1);
  for (let i=0; i<v.length; i++) need(Object.getOwnPropertyDescriptor(v, String(i))?.value !== undefined);
  return v;
}
function request(v: unknown): ObservationRequest {
  const x = object(v, ['project_id','edition_id','committed_operation_id','accepted_manifest_digest']);
  need(id(x.project_id) && id(x.edition_id) && hex(x.committed_operation_id,32) && hex(x.accepted_manifest_digest,64));
  return {project_id:x.project_id,edition_id:x.edition_id,committed_operation_id:x.committed_operation_id,accepted_manifest_digest:x.accepted_manifest_digest};
}
const sameRequest = (a: ObservationRequest, b: ObservationRequest) => Object.keys(a).every(key => a[key as keyof ObservationRequest] === b[key as keyof ObservationRequest]);
function file(v: unknown, observed: boolean): FileObservation | ExpectedFile {
  const x = object(v, observed ? ['role','name','volume','file_id','bytes','sha256'] : ['role','name','bytes','sha256']);
  need((x.role === 'EXE' || x.role === 'PCK') && artifactPath(x.name) && /^[A-Za-z0-9_-][A-Za-z0-9._-]{0,119}$/.test(x.name));
  need(x.name.toLowerCase().endsWith(x.role === 'EXE' ? '.exe' : '.pck'));
  need(Number.isSafeInteger(x.bytes) && Number(x.bytes) > 0 && Number(x.bytes) <= MAX_ARTIFACT_BYTES && hex(x.sha256,64));
  const base: ExpectedFile = {role:x.role,name:x.name,bytes:x.bytes as number,sha256:x.sha256};
  if (!observed) return base;
  need(hex(x.volume,16) && hex(x.file_id,32));
  return {...base,volume:x.volume,file_id:x.file_id};
}
export function validateObservationBinding(binding: ObservationBinding): ObservationBinding {
  const x=object(binding,['request','engine','sourceCommit','sourceTree','sourceManifestSha256','buildPlanSha256','requiresPck','files']);
  const req=request(x.request); need(id(x.engine) && hex(x.sourceCommit,40) && hex(x.sourceTree,40) && hex(x.sourceManifestSha256,64) && hex(x.buildPlanSha256,64) && typeof x.requiresPck === 'boolean');
  const files=list(x.files).map(v=>file(v,false) as ExpectedFile);
  need(files.filter(f=>f.role==='EXE').length===1 && files.filter(f=>f.role==='PCK').length===(x.requiresPck?1:0));
  need(new Set(files.map(f=>f.name.toLowerCase())).size===files.length && files.reduce((n,f)=>n+f.bytes,0)<=MAX_ARTIFACT_BYTES);
  return {request:req,engine:x.engine,sourceCommit:x.sourceCommit,sourceTree:x.sourceTree,sourceManifestSha256:x.sourceManifestSha256,buildPlanSha256:x.buildPlanSha256,requiresPck:x.requiresPck,files};
}

/** Object IPC only: no JSON report import, string parsing, filesystem access or
 * dispatch. A forged origin label cannot replace the admitted native bridge.
 */
export function parseNativeFileObservation(value: unknown, expected: ObservationBinding, now: number): NativeFileObservation {
  const binding=validateObservationBinding(expected);
  need(Number.isSafeInteger(now) && now >= 0);
  need(value!==null && typeof value==='object' && !Array.isArray(value));
  const desc=Object.getOwnPropertyDescriptor(value,'state'); need(desc && 'value' in desc);
  const common=['schema','state','read_only','execution_authority','gameplay','fidelity','observed_epoch_ms'];
  const x=object(value,desc.value==='HOLD'?[...common,'reason']:[...common,'selection','engine','source_commit','source_tree','source_manifest_sha256','build_plan_sha256','files']);
  need(x.schema==='OpenRemaster.NativeFileObservation.v1' && x.read_only===true && x.execution_authority===false && x.gameplay==='UNKNOWN' && x.fidelity==='UNKNOWN');
  need(Number.isSafeInteger(x.observed_epoch_ms) && Number(x.observed_epoch_ms)>=0 && Number(x.observed_epoch_ms)<=now && now-Number(x.observed_epoch_ms)<=TTL);
  const base: Common={schema:'OpenRemaster.NativeFileObservation.v1',read_only:true,execution_authority:false,gameplay:'UNKNOWN',fidelity:'UNKNOWN',observed_epoch_ms:x.observed_epoch_ms as number};
  if (x.state==='HOLD') {
    need(x.reason==='NO_ACCEPTED_SELECTION'||x.reason==='INVALID_REQUEST'||x.reason==='UNVERIFIED');
    return {...base,state:'HOLD',reason:x.reason};
  }
  need(x.state==='LIVE'); const selection=request(x.selection);
  need(sameRequest(selection,binding.request) && x.engine===binding.engine && x.source_commit===binding.sourceCommit && x.source_tree===binding.sourceTree && x.source_manifest_sha256===binding.sourceManifestSha256 && x.build_plan_sha256===binding.buildPlanSha256);
  const files=list(x.files).map(v=>file(v,true) as FileObservation); need(files.length===binding.files.length);
  need(new Set(files.map(f=>f.name.toLowerCase())).size===files.length && new Set(files.map(f=>f.volume+':'+f.file_id)).size===files.length);
  const roles=new Set<string>();
  for (const f of files) {
    need(!roles.has(f.role));roles.add(f.role);
    need(binding.files.some(b=>b.role===f.role&&b.name===f.name&&b.bytes===f.bytes&&b.sha256===f.sha256));
  }
  return {...base,state:'LIVE',selection,engine:binding.engine,source_commit:binding.sourceCommit,source_tree:binding.sourceTree,source_manifest_sha256:binding.sourceManifestSha256,build_plan_sha256:binding.buildPlanSha256,files};
}

export function observationProjectInput(value: NativeFileObservation, binding: ObservationBinding, now: number): ProjectInput | null {
  // Revalidate at the mapping boundary, including TTL; only source-bound data
  // from a configured native reader can reach a current physical projection.
  const parsed=parseNativeFileObservation(value,binding,now);
  if (parsed.state==='HOLD') return null;
  const identity={project:binding.request.project_id,edition:binding.request.edition_id};
  const artifacts=parsed.files.map(f=>({role:f.role,path:f.name,sha256:f.sha256}));
  return parseProjectInput({...identity,archived:false,capturedAt:parsed.observed_epoch_ms,origin:'HOST_READONLY',
    sourceCheckpoint:{...identity,checkpoint:parsed.source_manifest_sha256,commit:parsed.source_commit,tree:parsed.source_tree},
    build:{...identity,id:binding.request.committed_operation_id,commit:parsed.source_commit,tree:parsed.source_tree,engine:parsed.engine,artifacts,requiresPck:binding.requiresPck},
    observations:artifacts.map(f=>({...identity,buildId:binding.request.committed_operation_id,...f,exists:true,checkedAt:parsed.observed_epoch_ms,source:'NATIVE_FILE_READ'})),
    gameplay:null,fidelity:null,writers:[],admission:'UNKNOWN',blockers:[],nextSafeTask:null},identity,now,TTL);
}
