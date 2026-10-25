/**
 * UI-010: purely read-only Owner Approval Boundary r13 projection.
 * This module has no side effects, no approval actions, and no authority over
 * K003, signing, Windows accounts, workers or any native process.
 */
export type TrustStageId="A"|"B"|"C";
export type TrustStage={
 id:TrustStageId;
 title:string;
 sourceDescription:string;
 decision:"EXTERNAL_DECISION_NOT_RECORDED";
 blocked:true; mayExecute:false;
 prerequisiteTokens:string[];
 reviewerRoles:string[];
 requiredEvidence:string[];
 sourceArtifacts:string[];
};
export type TrustReview={
 schema:"OpenRemaster.StudioReleaseTrustReview.v1";
 release:"ORF-STUDIO-UI-20261018-r9";
 generatedUtc:string;
 status:"A_B_C_REVIEW_READY_EXTERNAL_APPROVALS_MISSING_PRODUCTION_HOLD";
 authority:"HISTORICAL_SOURCE_SHA_ONLY_UNSIGNED_SAME_ASSISTANT_REVIEW";
 parentR8ZipSha256:string;
 pins:Record<string,string>;
 checkpointStatus:"SOURCE_BOUND_OWNER_A_B_C_REVIEW_TESTS_PASS_PRODUCTION_HOLD";
 sourceDateUtc:string;
 sourceReview:"SELF_REVIEW_UNSIGNED_APPROVAL_PACKET_NOT_EXTERNAL_OWNER";
 negativeFirstSourceTests:82;
 sourceRolesVerified:11;
 inheritedNW013P0Blockers:10;
 inheritedR12NoGoDomains:7;
 sequentialStages:TrustStage[];
 executionPolicy:{
  scheduler:"EXISTING_K003_ONLY";
  oneWriter:true;maxGlobalHeavy:3;unknownOutcome:"HOLD_NO_AUTO_RETRY";
  forbidV1Fallback:true;immutableGames:true;
  nativeWorkerStateReportedAtSource:"Disabled";
  gatewayStateReportedAtSource:"Running";
  liveWindowsTaskQueriedByStudio:false;
  ownerIdentityAdmitted:false;witnessOffhostCurrent:false;
  ownerPublisherSignatureVerified:false;
  independentExternalReviewer:false;
  mayInstall:false;mayCreateCloudResources:false;mayStartWorker:false;
  mayDispatch:false;mayAutoRetry:false;approvedGUILease:false;
  currentProductionAuthority:"HOLD";
 };
 studioProduction:{
  moduleSourceRecords:20;requiredInstallerComponents:9;
  acceptedInstalledComponents:0;componentManagerCommissioned:false;
  portableHostHasRealInspectorLease:false;nativeTauriSignedExeBuilt:false;
  externalOperatorHandoffOnly:true;approvalsSubmittedThroughUi:false;
 };
 notice:string;
};
const exactPins={
 checkpoint:"0665200956d594f056e25599b8c2852672643c164024d02ac5e0bccc98e67ed5",
 reviewGates:"0814f0e74ca9da37e67ab5e2a20b9cefa3ea5ba60a589bf51b1cad3ec9509bf1",
 handoff:"a7a0e3bc342b3d5f74f7304236378684b4ade219ced277d5e7b30593b74c484a",
 studioR8Snapshot:"e885cd4c3d181d520c0afb68c07ed00bc53f49019e4e2110a6aa35c34c3f65d5",
 portableR8Snapshot:"197ac02fe62565efad4d8bbd7d303f1eb510f7ceef8bdfbf7a3a855a2f1954ed",
 parentR8Zip:"965bbe1aa6ff4a2eec4f0a2100e7802e4177d8511b217de6c37c93b7d0836fd2"
};
const stageDefinitions=[
 {id:"A",title:"Independent publisher, Owner & Witness trust",prereq:[],evidence:5},
 {id:"B",title:"Protected Windows roles and signed installer",
  prereq:["A_EXTERNAL_TRUST_ACCEPTANCE"],evidence:6},
 {id:"C",title:"V2 lifecycle, one writer & native canary",
  prereq:["A_EXTERNAL_TRUST_ACCEPTANCE","B_PROTECTED_INSTALL_ACCEPTANCE"],evidence:6}
] as const;
export const RELEASE_STAGES=stageDefinitions;
const plain=(value:unknown):value is Record<string,unknown> =>
 value!==null && typeof value==="object" && !Array.isArray(value);
const sameFields=(found:Record<string,unknown>,expected:Record<string,unknown>) =>
 Object.keys(found).sort().join("|")===Object.keys(expected).sort().join("|") &&
 Object.entries(expected).every(([k,v])=>found[k]===v);
const boundedStrings=(value:unknown,min:number,max:number,count:number):value is string[] =>
 Array.isArray(value)&&value.length===count &&
 value.every(x=>typeof x==="string" && x.length>=min && x.length<=max) &&
 new Set(value).size===value.length;
function stageIsValid(v:unknown,i:number):v is TrustStage{
 if(!plain(v))return false;
 const def=stageDefinitions[i];
 if(v.id!==def.id || v.title!==def.title ||
   v.decision!=="EXTERNAL_DECISION_NOT_RECORDED" || v.blocked!==true ||
   v.mayExecute!==false || typeof v.sourceDescription!=="string" ||
   v.sourceDescription.length<10 || v.sourceDescription.length>250 ||
   !Array.isArray(v.prerequisiteTokens) ||
   v.prerequisiteTokens.join("|")!==def.prereq.join("|") ||
   !boundedStrings(v.reviewerRoles,3,80,3) ||
   !boundedStrings(v.requiredEvidence,10,512,def.evidence) ||
   !boundedStrings(v.sourceArtifacts,4,120,3))return false;
 return sameFields(
   Object.fromEntries(Object.entries(v).filter(([key])=>!["sourceDescription","reviewerRoles","requiredEvidence","sourceArtifacts","prerequisiteTokens"].includes(key))),
   {id:def.id,title:def.title,decision:"EXTERNAL_DECISION_NOT_RECORDED",blocked:true,mayExecute:false}
 );
}
export function validateTrustReview(raw:unknown):raw is TrustReview{
 if(!plain(raw) || raw.schema!=="OpenRemaster.StudioReleaseTrustReview.v1" ||
   raw.release!=="ORF-STUDIO-UI-20261018-r9" ||
   raw.status!=="A_B_C_REVIEW_READY_EXTERNAL_APPROVALS_MISSING_PRODUCTION_HOLD" ||
   raw.authority!=="HISTORICAL_SOURCE_SHA_ONLY_UNSIGNED_SAME_ASSISTANT_REVIEW" ||
   raw.parentR8ZipSha256!==exactPins.parentR8Zip ||
   raw.checkpointStatus!=="SOURCE_BOUND_OWNER_A_B_C_REVIEW_TESTS_PASS_PRODUCTION_HOLD" ||
   raw.sourceReview!=="SELF_REVIEW_UNSIGNED_APPROVAL_PACKET_NOT_EXTERNAL_OWNER" ||
   typeof raw.generatedUtc!=="string" || !Number.isFinite(Date.parse(raw.generatedUtc)) ||
   typeof raw.sourceDateUtc!=="string" || !Number.isFinite(Date.parse(raw.sourceDateUtc)) ||
   raw.negativeFirstSourceTests!==82 || raw.sourceRolesVerified!==11 ||
   raw.inheritedNW013P0Blockers!==10 || raw.inheritedR12NoGoDomains!==7 ||
   typeof raw.notice!=="string" || raw.notice.length>450 ||
   !plain(raw.pins) || !sameFields(raw.pins,exactPins) ||
   !Array.isArray(raw.sequentialStages) || raw.sequentialStages.length!==3 ||
   !raw.sequentialStages.every(stageIsValid) ||
   !plain(raw.executionPolicy) || !plain(raw.studioProduction))return false;
 const policy={
  scheduler:"EXISTING_K003_ONLY",oneWriter:true,maxGlobalHeavy:3,
  unknownOutcome:"HOLD_NO_AUTO_RETRY",forbidV1Fallback:true,immutableGames:true,
  nativeWorkerStateReportedAtSource:"Disabled",gatewayStateReportedAtSource:"Running",
  liveWindowsTaskQueriedByStudio:false,ownerIdentityAdmitted:false,
  witnessOffhostCurrent:false,ownerPublisherSignatureVerified:false,
  independentExternalReviewer:false,mayInstall:false,mayCreateCloudResources:false,
  mayStartWorker:false,mayDispatch:false,mayAutoRetry:false,
  approvedGUILease:false,currentProductionAuthority:"HOLD"
 };
 const studio={
  moduleSourceRecords:20,requiredInstallerComponents:9,acceptedInstalledComponents:0,
  componentManagerCommissioned:false,portableHostHasRealInspectorLease:false,
  nativeTauriSignedExeBuilt:false,externalOperatorHandoffOnly:true,
  approvalsSubmittedThroughUi:false
 };
 return sameFields(raw.executionPolicy,policy) &&
  sameFields(raw.studioProduction,studio) &&
  Object.keys(raw).length===18;
}
export function trustView(raw:unknown){
 if(!validateTrustReview(raw))return {
   status:"HOLD" as const,phase:"TRUST_SOURCE_REJECTED" as const,review:null
 };
 return {
   status:"HOLD" as const,phase:"EXTERNAL_APPROVAL_REQUIRED" as const,review:raw
 };
}
/** Only prepare unsigned text for human review. NEVER express a consent action. */
export function renderUnsignedHandoff(record:TrustReview,stageId:TrustStageId):string{
 const stage=record.sequentialStages.find(s=>s.id===stageId);
 if(!stage)throw Error("UNKNOWN_REVIEW_STAGE");
 return [
  "OPENREMASTER STUDIO — UNSIGNED EXTERNAL REVIEW BRIEF",
  "No approval, consent, signature or production permission is granted by this document.",
  "Source: Owner Approval Boundary r13 (historical).",
  "Stage "+stage.id+" — "+stage.title,
  "Current decision: "+stage.decision,
  "Before review: "+(stage.prerequisiteTokens.length?stage.prerequisiteTokens.join(", "):"No preceding stage"),
  "",
  "Independent reviewing roles:",...stage.reviewerRoles.map(x=>"- "+x),
  "",
  "Evidence requested for external review:",...stage.requiredEvidence.map((x,i)=>(i+1)+". "+x),
  "",
  "Original source artifact references:",...stage.sourceArtifacts.map(x=>"- "+x),
  "",
  "Canonical source SHA-256: "+record.pins.reviewGates,
  "Parent UI source SHA-256: "+record.parentR8ZipSha256,
  "PRODUCTION HOLD / SINGLE WRITER / MAX 3 GLOBAL HEAVY / NO AUTO RETRY",
  "Submitting this document does not bypass A→B→C or constitute approval."
 ].join("\n")+"\n";
}
