/**
 * UI-013 bounded Inspector Host client / ARCHIVED SOURCE REPLAY ONLY.
 * No transport to native host, network request, Windows process, Owner lease,
 * scheduler, game or model. Pure method-correlated fail-closed state machine.
 *
 * A future *separately authorized* host transport may use the request/response
 * validator. This module itself cannot grant a production capability.
 */
export type InspectorMethod="health.get"|"checkpoints.list"|"checkpoints.get";
export type InspectorParams=Record<string,unknown>;
export type InspectorRequest={
  schema:"OpenRemaster.ContinuationInspector.Request.v1";version:"1.0.0";
  id:string;method:InspectorMethod;params:InspectorParams;
};
export type InspectorSecurity={
  authority:"SOURCE_BOUND_READONLY_PROJECTION";
  auto_retry:false;fidelity_verified:false;game_launch:false;model_calls:false;
  native_dispatch:false;owner_admitted:false;production_admission:"HOLD";
  read_only:true;runtime_verified:false;writes_allowed:false;
};
export type InspectorResponse={
  schema:"OpenRemaster.ContinuationInspector.Response.v1";version:"1.0.0";
  id:string;method:InspectorMethod;ok:boolean;security:InspectorSecurity;
  snapshot?:string;data?:Record<string,unknown>;
  error?:{code:string;status:"HOLD_NO_FALLBACK"};
};
export type ArchivedFixture={request:InspectorRequest;response:InspectorResponse};
export type ArchivedHostReport={
  schema:"OpenRemaster.StudioHostConnectorOfflineFixture.v1";
  release:"ORF-STUDIO-HOST-CONNECTOR-20261018-r1";
  generatedUtc:string;
  status:"HISTORICAL_REAL_WINDOWS_INSPECTOR_RESPONSES_REPLAY_ONLY_PRODUCTION_HOLD";
  authority:"UNSIGNED_FIXED_LOCAL_HOST_EVIDENCE_NO_LIVE_AUTHORITY";
  sourcePins:Record<string,string>;
  hostContract:{
    version:"1.0.0";requestSchema:string;responseSchema:string;
    transport:"ONE_SHOT_JSON_STDIO_TO_EOF_NO_LISTENER";allowedMethods:string[];
    maxRequestBytes:8192;maxResponseBytes:131072;
    clientPendingDeadlineMs:15000;clientFreshnessLimitMs:30000;
    hostDeadlineMs:8000;originalHostTestsPassed:201;
    realHistoricalWindowsHostRequests:6;
    historicalSuccessResponses:5;historicalSnapshotRejects:1;
  };
  archivedSnapshot:string;responseFixtures:ArchivedFixture[];
  security:Record<string,unknown>;
};
export const INPUT_LIMIT=8192;
export const OUTPUT_LIMIT=131072;
export const PENDING_MS=15000;
export const RETAIN_MS=30000;
export const REQUIRED_METHODS=["health.get","checkpoints.list","checkpoints.get"] as const;
const hex=/^[0-9a-f]{64}$/;
const sid=/^sha256:[0-9a-f]{64}$/;
const cid=/^cp_[0-9a-f]{64}$/;
const rid=/^[A-Za-z0-9_.:-]{1,64}$/;
const fixedSnapshot="sha256:20f15ecee63ea7daea2b8e9a72060e9348eee22b8d9bb085063a0bb687ce43e6";
const PINNED={
 parentR11:"8771434f02188076dd30e6638a2bb436e592f3b9a72224170d1c5e2589608417",
 hostCheckpoint:"3c0fcd236ed9b6a006dbe22480cac47e66a8287454214057e94f667cbd6e87ba",
 hostApiContract:"4883aa7a411b37cf0532ec4ba4bf30a280796f63f8728116c44cd57f5e5a6845",
 hostSession:"7b3b1cc23abb8b128dbd73bdcd80996e4bcdf9b41bbb850ab7edab4dec6e618c",
 windowsVerification:"a25293726e66ae2f57a520ff4f2a57f82da84fa041e4fbce4d5b3c45bcbf1a69",
 historicalRealHostPilot:"f579c57a366bcd6ae6bc99e8936f8a8d4c5628fda1d774c68b95f7167f0dd9d0",
 studioArchivedCapture:"8dd02986d98ece86ed7530c1ce302cb92d6a1fbb43b8799c2ac708011f259251"
};
const SECURITY={
 authority:"SOURCE_BOUND_READONLY_PROJECTION",
 auto_retry:false,fidelity_verified:false,game_launch:false,
 model_calls:false,native_dispatch:false,owner_admitted:false,
 production_admission:"HOLD",read_only:true,runtime_verified:false,
 writes_allowed:false
} as const;
const METHODS=["checkpoints.list","checkpoints.list","checkpoints.get","health.get","checkpoints.list","checkpoints.list"] as const;
const OK=[true,true,true,true,false,true];
const INPUT_FIELDS=["schema","version","id","method","params"];
const OUTPUT_GOOD=["schema","version","id","method","ok","security","snapshot","data"];
const OUTPUT_BAD=["schema","version","id","method","ok","security","error"];
const itemFields=["id","project","workstream","edition","scope","source_schema","source_sha256",
 "reported_status","reported_at_utc","parent_ids","observation_class","freshness"];
const plain=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==="object"&&!Array.isArray(v);
const exact=(obj:Record<string,unknown>,names:readonly string[]):boolean=>
 Object.keys(obj).sort().join("|")===[...names].sort().join("|");
const same=(obj:Record<string,unknown>,reference:Record<string,unknown>):boolean=>
 exact(obj,Object.keys(reference))&&Object.entries(reference).every(([k,v])=>obj[k]===v);
function assert(cond:unknown,reason:string):asserts cond {
 if(!cond)throw Error("INSPECTOR_PROTOCOL_HOLD_"+reason);
}
function typedParams(method:InspectorMethod,params:unknown):params is InspectorParams {
 if(!plain(params))return false;
 if(method==="health.get")return exact(params,[]);
 if(method==="checkpoints.list"){
  if(Object.keys(params).some(x=>!["limit","offset","if_snapshot"].includes(x)))return false;
  const limit=params.limit??20,offset=params.offset??0;
  if(!Number.isSafeInteger(limit)||Number(limit)<1||Number(limit)>20 ||
     !Number.isSafeInteger(offset)||Number(offset)<0||Number(offset)>128)return false;
  if(Number(offset)>0 && (typeof params.if_snapshot!=="string"||!sid.test(params.if_snapshot)))return false;
  if("if_snapshot" in params && (typeof params.if_snapshot!=="string"||!sid.test(params.if_snapshot)))return false;
  return true;
 }
 return exact(params,["id","if_snapshot"])&&
    typeof params.id==="string"&&cid.test(params.id)&&
    typeof params.if_snapshot==="string"&&sid.test(params.if_snapshot);
}
const utf8len=(v:unknown)=>new TextEncoder().encode(JSON.stringify(v)).length;
export function prepareRequest(id:string,method:InspectorMethod,params:unknown={}):InspectorRequest {
 assert(typeof id==="string"&&rid.test(id),"INVALID_REQUEST_ID");
 assert(REQUIRED_METHODS.includes(method),"METHOD_NOT_ALLOWED");
 assert(typedParams(method,params),"METHOD_PARAMS_REJECTED");
 const q={schema:"OpenRemaster.ContinuationInspector.Request.v1" as const,
  version:"1.0.0" as const,id,method,params:{...params}};
 assert(utf8len(q)<=INPUT_LIMIT,"INPUT_BYTES_LIMIT");
 Object.freeze(q.params);return Object.freeze(q);
}
function decisionIsHeld(v:unknown){
 if(!plain(v)||v.owner_selected_id!==null||v.production_admission!=="HOLD")return false;
 return v.status==="MULTI_WORKSTREAM_CONFLICT_OWNER_SELECTION_REQUIRED"&&
  Array.isArray(v.registry_blockers)&&v.registry_blockers.length===1&&
  v.registry_blockers[0]==="EXTERNAL_OWNER_CANONICAL_SELECTION_REQUIRED"&&
  Array.isArray(v.reason_codes)&&v.reason_codes.includes("PRODUCTION_HOST_NOT_BOUND");
}
function itemOk(v:unknown):boolean {
 if(!plain(v)||!exact(v,itemFields))return false;
 return typeof v.id==="string"&&cid.test(v.id)&&
  typeof v.source_sha256==="string"&&hex.test(v.source_sha256)&&
  ["project","workstream","edition","scope","source_schema","reported_status"].every(
   k=>typeof v[k]==="string"&&v[k].length>0&&v[k].length<=240)&&
  v.reported_at_utc===null && Array.isArray(v.parent_ids)&&v.parent_ids.length<=1&&
  v.parent_ids.every(x=>typeof x==="string"&&cid.test(x)&&x!==v.id)&&
  v.observation_class==="PINNED_CHECKPOINT_REPORT_NOT_OWNER_SIGNOFF"&&
  v.freshness==="MATCHES_PINNED_SHA256_NOT_LATEST_ASSERTION";
}
function dataOk(method:InspectorMethod,q:InspectorRequest,d:unknown):boolean{
 if(!plain(d) || !decisionIsHeld(d.decision) ||
   d.freshness!=="MATCHES_PINNED_SHA256_NOT_LATEST_ASSERTION" ||
   d.cache_generation!==1)return false;
 if(method==="health.get"){
  return exact(d,["cache_generation","checkpoint_count","decision","freshness","status"])&&
    d.checkpoint_count===2&&d.status==="READONLY_PROJECTION_AVAILABLE";
 }
 if(method==="checkpoints.list"){
  const fields=["cache_generation","count","decision","freshness","has_more","items","offset","total"];
  return exact(d,fields)&&Array.isArray(d.items)&&d.items.every(itemOk)&&
    Number.isSafeInteger(d.count)&&d.count===d.items.length&&d.total===2&&
    Number.isSafeInteger(d.offset)&&
    d.offset===(q.params.offset??0)&&
    typeof d.has_more==="boolean"&&
    d.has_more===(Number(d.offset)+Number(d.count)<Number(d.total));
 }
 return exact(d,["cache_generation","decision","freshness","item"])&&
   itemOk(d.item)&&plain(d.item)&&d.item.id===q.params.id;
}
export function validateResponse(raw:unknown,q:InspectorRequest):raw is InspectorResponse {
 if(!plain(raw)||raw.schema!=="OpenRemaster.ContinuationInspector.Response.v1"||
    raw.version!=="1.0.0"||raw.id!==q.id||raw.method!==q.method||
    !plain(raw.security)||!same(raw.security,SECURITY)||
    utf8len(raw)>OUTPUT_LIMIT)return false;
 if(raw.ok===false) {
   return exact(raw,OUTPUT_BAD)&&plain(raw.error)&&
     exact(raw.error,["code","status"])&&
     raw.error.code==="SNAPSHOT_CHANGED"&&raw.error.status==="HOLD_NO_FALLBACK";
 }
 if(raw.ok!==true||!exact(raw,OUTPUT_GOOD)||
    raw.snapshot!==fixedSnapshot ||!dataOk(q.method,q,raw.data))return false;
 if(q.method!=="health.get"&&typeof q.params.if_snapshot==="string"&&
    raw.snapshot!==q.params.if_snapshot)return false;
 return true;
}
function validFixture(row:unknown,i:number):row is ArchivedFixture {
 if(!plain(row)||!exact(row,["request","response"])||!plain(row.request))return false;
 const q=row.request;
 if(!exact(q,INPUT_FIELDS)||q.id!=="host-real-"+(i+1)||q.method!==METHODS[i])return false;
 try {
  const built=prepareRequest(q.id as string,q.method as InspectorMethod,q.params);
  if(q.schema!==built.schema||q.version!==built.version||q.id!==built.id||
     q.method!==built.method||!plain(q.params)||
     !same(q.params,built.params))return false;
  if(!validateResponse(row.response,built))return false;
  return plain(row.response)&&row.response.ok===OK[i];
 }catch{return false;}
}
export function validateArchivedHost(raw:unknown):raw is ArchivedHostReport {
 if(!plain(raw)||
  raw.schema!=="OpenRemaster.StudioHostConnectorOfflineFixture.v1" ||
  raw.release!=="ORF-STUDIO-HOST-CONNECTOR-20261018-r1" ||
  raw.status!=="HISTORICAL_REAL_WINDOWS_INSPECTOR_RESPONSES_REPLAY_ONLY_PRODUCTION_HOLD" ||
  raw.authority!=="UNSIGNED_FIXED_LOCAL_HOST_EVIDENCE_NO_LIVE_AUTHORITY" ||
  typeof raw.generatedUtc!=="string"||!Number.isFinite(Date.parse(raw.generatedUtc))||
  !plain(raw.sourcePins)||!same(raw.sourcePins,PINNED)||
  !plain(raw.hostContract)||!plain(raw.security)||
  raw.archivedSnapshot!==fixedSnapshot||
  !Array.isArray(raw.responseFixtures)||raw.responseFixtures.length!==6||
  !raw.responseFixtures.every(validFixture)||!exact(raw,[
   "schema","release","generatedUtc","status","authority","sourcePins",
   "hostContract","archivedSnapshot","responseFixtures","security"]))return false;
 const base={
  version:"1.0.0",
  requestSchema:"OpenRemaster.ContinuationInspector.Request.v1",
  responseSchema:"OpenRemaster.ContinuationInspector.Response.v1",
  transport:"ONE_SHOT_JSON_STDIO_TO_EOF_NO_LISTENER",
  maxRequestBytes:8192,maxResponseBytes:131072,
  clientPendingDeadlineMs:15000,clientFreshnessLimitMs:30000,
  hostDeadlineMs:8000,originalHostTestsPassed:201,
  realHistoricalWindowsHostRequests:6,historicalSuccessResponses:5,
  historicalSnapshotRejects:1
 };
 const {allowedMethods,...otherContract}=raw.hostContract;
 if(!same(otherContract,base)||!Array.isArray(allowedMethods)||
    allowedMethods.join("|")!==REQUIRED_METHODS.join("|"))return false;
 const posture={
  sourceContext:"HISTORICAL_HOST_PILOT_NOT_CURRENT",
  archiveCanDemonstrateTransportContract:true,
  liveHostConnected:false,originalHostExecutedNow:false,
  currentWindowsUserRoleAuthenticated:false,currentOwnerAdmitted:false,
  currentWitnessAdmitted:false,currentGuiLease:false,signedPublisher:false,
  originalGamesTouched:false,nativeDispatch:false,autoRetry:false,
  canInstall:false,canStartWorker:false,canRunModel:false,canCommitJob:false,
  productionStatus:"HOLD_NO_AUTO_RETRY"
 };
 return same(raw.security,posture);
}
export type SessionPhase="HOLD"|"LOADING"|"ARCHIVED_RESPONSE"|"CLOSED";
export type SessionState={
 phase:SessionPhase;code:string;requestId:string|null;method:InspectorMethod|null;
 archivedItems:readonly unknown[];archiveResponse:InspectorResponse|null;
 ownerAdmitted:false;workerAuthorized:false;canDispatch:false;canRetry:false;
};
export type SessionTicket={readonly id:string;readonly seq:number;readonly beganMs:number;readonly request:InspectorRequest};
export function createConnectorSession(config:{now:()=>number}){
 let serial=0;let closed=false;
 let pending:SessionTicket|null=null;
 let expires:number|null=null;
 let state:SessionState=held("NO_OBSERVATION");
 function held(code:string,phase:SessionPhase="HOLD"):SessionState{
  return Object.freeze({
   phase,code,requestId:null,method:null,archivedItems:Object.freeze([]),
   archiveResponse:null,ownerAdmitted:false,workerAuthorized:false,
   canDispatch:false,canRetry:false
  });
 }
 function clear(code:string,phase:SessionPhase="HOLD"){
  pending=null;expires=null;state=held(code,phase);
 }
 function time(){const v=config.now();assert(Number.isFinite(v)&&v>=0,"NONMONOTONIC_CLOCK");return v;}
 function expire(){const t=time();if(expires!==null&&t>=expires)
  clear(pending?"REQUEST_TIMEOUT":"OBSERVATION_EXPIRED");}
 function begin(method:InspectorMethod,params:unknown={}){
  if(closed)throw Error("SESSION_CLOSED");
  clear("REQUEST_REPLACED"); // stale cards vanish before validating request
  const id="studio-archived-"+(++serial);
  let request:InspectorRequest;
  try {request=prepareRequest(id,method,params);}
  catch(error){clear("BAD_REQUEST");throw error;}
  const ticket=Object.freeze({id,seq:serial,beganMs:time(),request});
  pending=ticket;expires=ticket.beganMs+PENDING_MS;
  state=Object.freeze({phase:"LOADING" as const,code:"ARCHIVED_REPLAY_PENDING",
   requestId:id,method,archivedItems:[],archiveResponse:null,
   ownerAdmitted:false as const,workerAuthorized:false as const,
   canDispatch:false as const,canRetry:false as const});
  return ticket;
 }
 function complete(ticket:SessionTicket,raw:unknown){
  expire();
  if(closed||pending!==ticket)return false;
  if(time()<ticket.beganMs){clear("MONOTONIC_TIME_REVERSED");return false;}
  if(!validateResponse(raw,ticket.request)){clear("UNTRUSTED_RESPONSE");return false;}
  if(!plain(raw)||raw.ok!==true){clear("ARCHIVED_SNAPSHOT_REJECTED");return false;}
  pending=null;
  expires=ticket.beganMs+RETAIN_MS;
  const data=raw.data as Record<string,unknown>;
  const rows=ticket.request.method==="checkpoints.list" ?
    data.items as unknown[] : ticket.request.method==="checkpoints.get"?[data.item]:[];
  state=Object.freeze({phase:"ARCHIVED_RESPONSE",code:"HISTORICAL_SNAPSHOT_ONLY",
   requestId:ticket.id,method:ticket.request.method,archivedItems:rows,
   archiveResponse:raw as InspectorResponse,
   ownerAdmitted:false,workerAuthorized:false,canDispatch:false,canRetry:false});
  return true;
 }
 function fail(ticket:SessionTicket,code="TRANSPORT_HOLD"){
  expire();
  if(closed||pending!==ticket)return false;
  clear(/^[A-Z0-9_]{2,64}$/.test(code)?code:"TRANSPORT_HOLD");return true;
 }
 function snapshot():SessionState{expire();return state;}
 function cancel(){if(!closed)clear("REQUEST_CANCELLED");}
 function close(){if(!closed){closed=true;clear("SESSION_CLOSED","CLOSED");}}
 return Object.freeze({begin,complete,fail,snapshot,cancel,close});
}
/** The archived fixture correlation is remapped ONLY within this local demo. */
export function replayArchivedFixture(session:ReturnType<typeof createConnectorSession>,report:ArchivedHostReport,index:number){
 assert(validateArchivedHost(report),"SOURCE_FIXTURE_UNTRUSTED");
 assert(Number.isInteger(index)&&index>=0&&index<report.responseFixtures.length,"FIXTURE_INDEX");
 const fixture=report.responseFixtures[index];
 const ticket=session.begin(fixture.request.method,fixture.request.params);
 const rewritten={...fixture.response,id:ticket.id};
 const accepted=session.complete(ticket,rewritten);
 return {accepted,state:session.snapshot(),requestedMethod:ticket.request.method};
}
