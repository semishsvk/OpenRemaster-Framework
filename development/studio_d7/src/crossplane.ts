/**
 * Studio-side display adapter for the local Framework ↔ ORION crossplane.
 * Local source hashes and a fresh file read do NOT authenticate live service state.
 * All receipt content is untrusted. This module has no authority-bearing action.
 */
export type CrossplaneTask = {
  taskId: string; operationId: string; inputSha256: string;
  orionStatus: "HOLD"; routeReason: "NO_ELIGIBLE_PROFILE";
  selectedProfileId: null; modelInvoked: false; nativeAdmitted: false; dispatchExecuted: false;
};
export type CrossplaneCapture = {
  schema: "OpenRemaster.StudioCrossplaneCapture.v1";
  status: "SOURCE_BOUND_READONLY_HOLD" | "HOLD"; code: string;
  sourceMode: "MANUAL_PINNED_LOCAL_CLI";
  sourceAuthority: "LOCAL_UNSIGNED_SHA_ONLY";
  sourceScope: "EXACT_12_INPUTS_NOT_GLOBAL";
  capturedUtc: string | null; manifestSha256: string | null; workPackageSha256: string | null;
  nativeHistoricalState: "Disabled" | "Running" | "Ready" | "Unknown" | null;
  nativeObservationCurrent: boolean; nativeAgeSeconds: number | null;
  sourceHashes: Record<string,string>; reasonCodes: string[]; tasks: CrossplaneTask[];
  cliExitCode: 75 | null; evidenceCoherent: boolean;
  productionAdmission:"HOLD"; dispatchAuthorized:false; modelInvocationAuthorized:false;
  nativeWorkerStartAuthorized:false; leaseAuthorized:false; automaticRetry:false;
  independentReview:false; liveAuthorityVerified:false; productionAuthority:false;
};
export type CrossplanePhase = "HOLD" | "PINNED_SOURCE_ONLY" | "STALE_CAPTURE";
export type CrossplaneView = {
  phase: CrossplanePhase; code: string; data: CrossplaneCapture | null;
  activeLiveJobs: 0; productionCanExecute: false;
};
const hashes = /^[0-9a-f]{64}$/;
const reason = /^[A-Z][A-Z0-9_]{2,95}$/;
const isoUtc = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/;
const roles = ["active_k003","agents","native_r4_evidence","orion_r3_checkpoint",
  "orion_r3_routing","owner_backend_checkpoint","owner_backend_service","r11_checkpoint",
  "r11_k003_adapter","r11_orion_bridge","r11_proposal","r11_work_package"];
const acceptedReasons = new Set(["K003_EXTERNAL_OWNER_ADMISSION_MISSING",
  "OWNER_AND_WITNESS_ONLY_LOCAL_TEST","ORION_BENCHMARK_ROOTS_ONLY_LOCAL_TEST",
  "NATIVE_WORKER_IDENTITY_AND_SIGNED_TERMINALS_MISSING",
  "R11_CYCLE_SELF_REVIEW_NOT_PRODUCTION_ACCEPTANCE",
  "NATIVE_WORKER_NOT_RUNNING","NATIVE_OBSERVATION_STALE"]);
const fixedFields = ["schema","status","code","sourceMode","sourceAuthority","sourceScope",
  "capturedUtc","manifestSha256","workPackageSha256","nativeHistoricalState",
  "nativeObservationCurrent","nativeAgeSeconds","sourceHashes","reasonCodes","tasks",
  "cliExitCode","evidenceCoherent","productionAdmission","dispatchAuthorized",
  "modelInvocationAuthorized","nativeWorkerStartAuthorized","leaseAuthorized",
  "automaticRetry","independentReview","liveAuthorityVerified","productionAuthority"];
const plain = (x: unknown): x is Record<string,unknown> =>
  x!==null && typeof x==="object" && !Array.isArray(x);
const keys = (x: Record<string,unknown>, allowed: readonly string[]): boolean =>
  Object.keys(x).sort().join("|") === [...allowed].sort().join("|");
const isSha = (x: unknown): x is string => typeof x==="string" && hashes.test(x);
const falseAuthority = (x: Record<string,unknown>): boolean =>
  x.productionAdmission==="HOLD" && x.dispatchAuthorized===false &&
  x.modelInvocationAuthorized===false && x.nativeWorkerStartAuthorized===false &&
  x.leaseAuthorized===false && x.automaticRetry===false &&
  x.independentReview===false && x.liveAuthorityVerified===false &&
  x.productionAuthority===false;
const taskFields = ["taskId","operationId","inputSha256","orionStatus","routeReason",
  "selectedProfileId","modelInvoked","nativeAdmitted","dispatchExecuted"];
function taskOK(raw: unknown, i: number): raw is CrossplaneTask {
  if (!plain(raw) || !keys(raw,taskFields)) return false;
  const id = "T"+(i+1);
  return raw.taskId===id && raw.operationId==="cycle-20261018-r11-"+id &&
    isSha(raw.inputSha256) && raw.orionStatus==="HOLD" &&
    raw.routeReason==="NO_ELIGIBLE_PROFILE" &&
    raw.selectedProfileId===null && raw.modelInvoked===false &&
    raw.nativeAdmitted===false && raw.dispatchExecuted===false;
}
export function validateCrossplane(raw: unknown): raw is CrossplaneCapture {
  if (!plain(raw) || !keys(raw,fixedFields) ||
    raw.schema!=="OpenRemaster.StudioCrossplaneCapture.v1" ||
    raw.sourceMode!=="MANUAL_PINNED_LOCAL_CLI" ||
    raw.sourceAuthority!=="LOCAL_UNSIGNED_SHA_ONLY" ||
    raw.sourceScope!=="EXACT_12_INPUTS_NOT_GLOBAL" ||
    !falseAuthority(raw) || typeof raw.code!=="string" || !reason.test(raw.code) ||
    !plain(raw.sourceHashes) || !Array.isArray(raw.reasonCodes) ||
    !Array.isArray(raw.tasks)) return false;
  if (raw.status==="HOLD") {
    return raw.capturedUtc===null && raw.manifestSha256===null &&
      raw.workPackageSha256===null && raw.nativeHistoricalState===null &&
      raw.nativeObservationCurrent===false && raw.nativeAgeSeconds===null &&
      raw.cliExitCode===null && raw.evidenceCoherent===false &&
      Object.keys(raw.sourceHashes).length===0 &&
      raw.reasonCodes.length===0 && raw.tasks.length===0;
  }
  if (raw.status!=="SOURCE_BOUND_READONLY_HOLD" ||
    raw.code!=="CROSSPLANE_LOCAL_SOURCE_INSPECTED" ||
    raw.cliExitCode!==75 || raw.evidenceCoherent!==true ||
    !isSha(raw.manifestSha256) || !isSha(raw.workPackageSha256) ||
    typeof raw.capturedUtc!=="string" || !isoUtc.test(raw.capturedUtc) ||
    !Number.isFinite(Date.parse(raw.capturedUtc)) ||
    !["Disabled","Running","Ready","Unknown"].includes(String(raw.nativeHistoricalState)) ||
    typeof raw.nativeObservationCurrent!=="boolean" ||
    typeof raw.nativeAgeSeconds!=="number" || !Number.isFinite(raw.nativeAgeSeconds) ||
    raw.nativeAgeSeconds<0 ||
    raw.nativeObservationCurrent!==(raw.nativeAgeSeconds<=15) ||
    !keys(raw.sourceHashes,roles) ||
    !roles.every(role=>isSha((raw.sourceHashes as Record<string,unknown>)[role])) ||
    raw.reasonCodes.length<5 || raw.reasonCodes.length>7 ||
    new Set(raw.reasonCodes).size!==raw.reasonCodes.length ||
    !raw.reasonCodes.every(c=>typeof c==="string" && acceptedReasons.has(c)) ||
    raw.tasks.length!==5 ||
    !raw.tasks.every((t,i)=>taskOK(t,i))) return false;
  return raw.reasonCodes.includes("K003_EXTERNAL_OWNER_ADMISSION_MISSING") &&
    raw.reasonCodes.includes("OWNER_AND_WITNESS_ONLY_LOCAL_TEST") &&
    raw.reasonCodes.includes("R11_CYCLE_SELF_REVIEW_NOT_PRODUCTION_ACCEPTANCE") &&
    (raw.reasonCodes.includes("NATIVE_OBSERVATION_STALE") === !raw.nativeObservationCurrent) &&
    (raw.reasonCodes.includes("NATIVE_WORKER_NOT_RUNNING") === (raw.nativeHistoricalState!=="Running"));
}
export function classifyCrossplane(raw: unknown, nowMs: number = Date.now()): CrossplaneView {
  const held=(code:string):CrossplaneView=>({phase:"HOLD",code,data:null,activeLiveJobs:0,productionCanExecute:false});
  if(!validateCrossplane(raw)) return held("INVALID_OR_UNTRUSTED_CAPTURE");
  if(raw.status==="HOLD") return held(raw.code);
  const stamp=Date.parse(raw.capturedUtc!);
  if(!Number.isFinite(nowMs) || nowMs<stamp-1000) return held("FUTURE_OR_INVALID_LOCAL_CLOCK");
  const recent=nowMs-stamp<=30_000 && raw.nativeObservationCurrent;
  return {phase:recent?"PINNED_SOURCE_ONLY":"STALE_CAPTURE",
    code:recent?"PINNED_LOCAL_EVIDENCE_NOT_AUTHORITY":"ARCHIVED_OR_STALE_OBSERVATION",
    data:raw,activeLiveJobs:0,productionCanExecute:false};
}
