/** Strict display-only projection of frozen ORION/K003/Governor Lifecycle r2.
 * Data is local, archived, synthetic, unsigned. A checksum never admits a job.
 */
export type TaskRow={
  id:string; operationId:string; goal:string; dependsOn:string[];
  running:false; ownerAdmitted:false
};
export type Choice={
  status:"ONE_READY_SHADOW_CANDIDATE_HOLD"|"NO_READY_CANDIDATE_HOLD"|"INVALID_OR_UNTRUSTED_PLAN_HOLD";
  taskId:string|null;published:number;suppressed:number;proposalSha256:string|null;
  executionPermitted:false
};
export type Recheck={
  status:"UNCHANGED_SHADOW_PROPOSAL_HOLD"|"STALE_OR_CHANGED_PROPOSAL_HOLD";
  proposalSha256:string;unchanged:boolean;mayRetry:false;mayExecute:false
};
export type BoundedPlanEvidence={
  schema:"OpenRemaster.StudioBoundedPlanEvidence.v1";
  status:"ARCHIVED_SINGLE_TASK_SHADOW_HOLD";
  sourceAuthority:"UNSIGNED_LOCAL_SHA256_ONLY";
  observationMode:"HISTORICAL_SYNTHETIC_NOT_LIVE";
  zipSha256:string;sourceMemberHashes:Record<string,string>;
  originalK003Sha256:string;checkpointRecordedUtc:string;
  historicalTests:{orion:115;governor:15;planner:40;lifecycle:45;total:215};
  tasks:TaskRow[];
  scenarios:{
    initial:Choice;afterPass:Choice;completed:Choice;gameGpu:Choice;
    gameOffGpu:Choice;unknownPrior:Choice;unchanged:Recheck;changed:Recheck;
  };
  initialNextTaskId:"T1";afterFirstPassNextTaskId:"T2";
  globalHeavyMaximum:3;singleWriter:true;maxPublishedModelPlans:1;
  productionAdmission:"HOLD_NO_AUTO_RETRY";
  dispatchAuthorized:false;modelInvocationAuthorized:false;
  workerStartAuthorized:false;leaseAuthorized:false;automaticRetry:false;
  independentOwnerAuthenticated:false;independentWitnessAuthenticated:false;
  productionAdmitted:false;signedLifecycleVerified:false;currentNativeWorkerObserved:false
};
export type BoundedView={
  phase:"ARCHIVED_EVIDENCE_ONLY"|"HOLD";code:string;data:BoundedPlanEvidence|null;
  currentRunnableTasks:0;productionCanExecute:false
};
const sha=/^[0-9a-f]{64}$/;
const fixedZip="f7f47d1531f41c0e5b0332a269b4fda69ca68f8259c353e430708cd92f0bb9d4";
const fixedK003="644f9ef4d001a56ee9738d91ac558c5fed32967a17819245a3174b0815fe1d7a";
const members:Record<string,string>={
  checkpoint:"6ef137d8cbdd97d08368b344bf14405badf54b3df6b4648682147d6418f4cf4e",
  scenarios:"4b3115e3627c13826315614b8867f379b0279ad4c627f4f7e59de7675b697fbd",
  work_package:"0bad979f285838c1b6b0e22960afd6c143af8d5933119415897477a6a4f4f13b"
};
const falseFlags=["dispatchAuthorized","modelInvocationAuthorized",
  "workerStartAuthorized","leaseAuthorized","automaticRetry",
  "independentOwnerAuthenticated","independentWitnessAuthenticated",
  "productionAdmitted","signedLifecycleVerified","currentNativeWorkerObserved"];
const header=[
  "schema","status","sourceAuthority","observationMode","zipSha256",
  "sourceMemberHashes","originalK003Sha256","checkpointRecordedUtc",
  "historicalTests","tasks","scenarios","initialNextTaskId",
  "afterFirstPassNextTaskId","globalHeavyMaximum","singleWriter",
  "maxPublishedModelPlans","productionAdmission",...falseFlags
];
const taskFields=["id","operationId","goal","dependsOn","running","ownerAdmitted"];
const pickFields=["status","taskId","published","suppressed","proposalSha256","executionPermitted"];
const recheckFields=["status","proposalSha256","unchanged","mayRetry","mayExecute"];
const scenarios=["initial","afterPass","completed","gameGpu",
  "gameOffGpu","unknownPrior","unchanged","changed"];
const originalGoals=["Pinned historical snapshot","Original K003 validation",
  "Historical receipt chain","Historical CLI","Qualification and boundary"];
function plain(x:unknown):x is Record<string,unknown> {
  return x!==null && typeof x==="object" && !Array.isArray(x);
}
function exact(x:Record<string,unknown>,fields:readonly string[]):boolean {
  return Object.keys(x).sort().join("|")===[...fields].sort().join("|");
}
const isSha=(x:unknown)=>typeof x==="string" && sha.test(x);
function choiceValid(x:unknown,status:string,id:string|null,published:number,suppressed:number):boolean {
  if(!plain(x) || !exact(x,pickFields) || x.status!==status ||
     x.taskId!==id || x.published!==published || x.suppressed!==suppressed ||
     x.executionPermitted!==false)return false;
  return id===null && status==="INVALID_OR_UNTRUSTED_PLAN_HOLD" ?
    x.proposalSha256===null : isSha(x.proposalSha256);
}
function recheckValid(x:unknown,status:string,unchanged:boolean,initialHash:string):boolean {
  return plain(x) && exact(x,recheckFields) && x.status===status &&
    x.unchanged===unchanged && x.proposalSha256===initialHash &&
    x.mayExecute===false && x.mayRetry===false;
}
export function validateBoundedPlan(raw:unknown):raw is BoundedPlanEvidence {
  if(!plain(raw) || !exact(raw,header) ||
    raw.schema!=="OpenRemaster.StudioBoundedPlanEvidence.v1" ||
    raw.status!=="ARCHIVED_SINGLE_TASK_SHADOW_HOLD" ||
    raw.sourceAuthority!=="UNSIGNED_LOCAL_SHA256_ONLY" ||
    raw.observationMode!=="HISTORICAL_SYNTHETIC_NOT_LIVE" ||
    raw.zipSha256!==fixedZip || raw.originalK003Sha256!==fixedK003 ||
    !plain(raw.sourceMemberHashes) || !exact(raw.sourceMemberHashes,Object.keys(members)) ||
    !Object.entries(members).every(([k,v])=>(raw.sourceMemberHashes as Record<string,unknown>)[k]===v) ||
    falseFlags.some(k=>raw[k]!==false) ||
    raw.globalHeavyMaximum!==3 || raw.singleWriter!==true ||
    raw.maxPublishedModelPlans!==1 ||
    raw.productionAdmission!=="HOLD_NO_AUTO_RETRY" ||
    raw.initialNextTaskId!=="T1" || raw.afterFirstPassNextTaskId!=="T2" ||
    typeof raw.checkpointRecordedUtc!=="string" ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,9}\+00:00$/.test(raw.checkpointRecordedUtc) ||
    !Number.isFinite(Date.parse(raw.checkpointRecordedUtc)))return false;
  const counts=raw.historicalTests;
  if(!plain(counts) || !exact(counts,["orion","governor","planner","lifecycle","total"]) ||
    counts.orion!==115 || counts.governor!==15 || counts.planner!==40 ||
    counts.lifecycle!==45 || counts.total!==215)return false;
  if(!Array.isArray(raw.tasks) || raw.tasks.length!==5)return false;
  for(let i=0;i<5;i++){
    const x:unknown=raw.tasks[i];
    const id="T"+(i+1);
    if(!plain(x) || !exact(x,taskFields) ||
      x.id!==id || x.operationId!=="cycle-20261018-r11-"+id ||
      x.goal!==originalGoals[i] || x.running!==false || x.ownerAdmitted!==false ||
      !Array.isArray(x.dependsOn) ||
      x.dependsOn.length!==(i===0?0:1) ||
      (i>0 && x.dependsOn[0]!=="T"+i))return false;
  }
  if(!plain(raw.scenarios) || !exact(raw.scenarios,scenarios))return false;
  const s=raw.scenarios;
  const ready="ONE_READY_SHADOW_CANDIDATE_HOLD";
  const none="NO_READY_CANDIDATE_HOLD";
  if(!choiceValid(s.initial,ready,"T1",1,4) ||
    !choiceValid(s.afterPass,ready,"T2",1,3) ||
    !choiceValid(s.completed,none,null,0,0) ||
    !choiceValid(s.gameGpu,none,null,0,0) ||
    !choiceValid(s.gameOffGpu,ready,"T1",1,4) ||
    !choiceValid(s.unknownPrior,"INVALID_OR_UNTRUSTED_PLAN_HOLD",null,0,0))return false;
  const originalHash=(s.initial as Choice).proposalSha256;
  return typeof originalHash==="string" &&
    recheckValid(s.unchanged,"UNCHANGED_SHADOW_PROPOSAL_HOLD",true,originalHash) &&
    recheckValid(s.changed,"STALE_OR_CHANGED_PROPOSAL_HOLD",false,originalHash) &&
    // Synthetic progress and explicit Settings OFF must yield *new* local proposal digests.
    (s.afterPass as Choice).proposalSha256!==originalHash &&
    (s.gameOffGpu as Choice).proposalSha256!==originalHash;
}
export function boundedPlanView(raw:unknown):BoundedView {
  if(!validateBoundedPlan(raw))
    return {phase:"HOLD",code:"ARCHIVE_INVALID_OR_UNAVAILABLE",data:null,
      currentRunnableTasks:0,productionCanExecute:false};
  return {phase:"ARCHIVED_EVIDENCE_ONLY",code:"LOCAL_SIGNLESS_HISTORICAL_SHADOW_HOLD",
    data:raw,currentRunnableTasks:0,productionCanExecute:false};
}
