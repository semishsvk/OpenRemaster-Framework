/** UI-015 Native Build Lab — historical MSVC smoke evidence, never a Studio EXE.
 * Strict immutable source-only assertions; no compiler, installer, process,
 * model, current Owner, game or Windows task can be called from this module.
 */
export const NATIVE_GATES=["T01","T02","T03","T04","T05","T06","T07","T08","T09"] as const;
export type NativeGateId=typeof NATIVE_GATES[number];
export const BUILD_STEPS=["D01","D02","D03","D04","D05","D06","D07"] as const;
export const NATIVE_SOURCE_PINS={
 studioR13:"305ecd7fa56324cc8511d81cde8f69ac872cd888e0218d7a8ac56201fb002975",
 nativeR24Sealed:"61ec7a029d4d019607a2f92f938346b2c972be1d50a85ddb57f8329040802baa",
 originalK003:"644f9ef4d001a56ee9738d91ac558c5fed32967a17819245a3174b0815fe1d7a",
 desktopContractR22:"48808670f3c4c116ab007198fa3539d0234d40d614890fc0fdc973b938ce29a9",
 tauriTestOverlayR22:"46ba0820337772553000c2fb28ee2001382acc5a186a963230f38f832e0dfb4a",
 toolchainInventoryR23:"6f87b72d2b44d934c5c8fffb5032940f032506dab2470c07e1a5d00784c1b3ed",
 nativeCheckpointR24:"e68dc63f242efad9a4203ccd3be933eaffb884fbb7cf1ac2accfab9eb49642ad",
 nativeGateDeltaR24:"ad9cdf6b9a7082576d29ad586f5f24e0838b87ba737bac2bcd9d2dac64dd47ef",
 microsoftVendorSignaturesR24:"fa9c77e2bd3efb9d6c416f9a1987a1df7b58313974956ac4572096ac9bc95f3b",
 nativeValidationR24:"7fff43b24c388a07505a7609b6048d63af54425c7d854aaeb7ed05fb7310bc1b",
 nativeSyntheticStdoutR24:"96d0fae991c24bdf4175347b4ecd3274c40b8e571886c6458cbe90ec224705ce"
} as const;
export const SYNTHETIC_EXE_SHA="02df3045dd18966e85bbb3f79eca48608a95eef5d8b85721da3b051b0390626e";
export type NativeBuildReport={
 schema:"OpenRemaster.StudioNativeBuildReview.v1";
 release:"ORF-STUDIO-UI-20261018-r14";
 generatedUtc:string;
 status:"REAL_MSVC_SYNTHETIC_SMOKE_SOURCE_PROVEN__TAURI_AND_OWNER_RELEASE_HOLD";
 authority:"HISTORICAL_SAME_MACHINE_SOURCE_SHA_NOT_CURRENT_RELEASE_SIGNOFF";
 sourcePins:Record<string,string>;
 stage:"OFFLINE_READONLY_TECHNICAL_EVIDENCE";
 gates:{
  id:NativeGateId;name:string;readyHistorical:boolean;wasReadyInR23:boolean;
  reason:string;prerequisites:string;acceptedForProduction:false;
 }[];
 requiredSteps:{
  id:typeof BUILD_STEPS[number];title:string;
  sourceStatus:"MISSING"|"BLOCKED"|"NOT_VERIFIED"|"NOT_AUTHORIZED";
  needs:string;releaseAccepted:false;
 }[];
 progress:{
  historicalPriorReady:1;historicalNowReady:2;totalTechnicalGates:9;
  historicalRemaining:7;changedGate:"T02";
  syntheticExecutableProduced:true;syntheticExeSha256:string;
  realStudioTauriAppProduced:false;prebuiltMicrosoftSDKProven:true;
  preinstalledMSVCCompilerProven:true;publisherApproved:false;
  approvedOriginalOrionIconLocated:false;independentOwnerA_B_CApproved:false;
  signedOneInstallerCreated:false;admittedProductionComponents:0;
 };
 tooling:{
  msvcVersion:string;visualStudioVersion:string;sdkVersion:string;
  historicalSignedMicrosoftTools:{role:string;sha256:string;
   microsoftCodeSignatureValidAtR24:true;publisherIsOpenRemaster:false;}[];
  historicalR24SoftwareTests:19;newWin64ProcessExecutionByStudio:false;
  syntheticWin64SmokeActualExecutedAtR24:true;
  sourceOnlyReferenceNoExecutableCopied:true;syntheticExeIsNotStudioExe:true;
 };
 pe:{
  kind:"PE32_PLUS_CONSOLE_SYNTHETIC";amd64:true;aslr:true;
  highEntropyAslr:true;nxDep:true;sections:5;win64PointerBits:64;
  realTauriUiRendered:false;
 };
 production:{
  status:"HOLD_NO_AUTO_RETRY";
  mayInstall:false;mayDispatch:false;mayStartNativeWorker:false;
  mayAutoRetry:false;newSchedulerCreated:false;
  originalGamesOpenedOrModified:false;originalK003Modified:false;
  windowsAccountsServicesOrTasksModified:false;
  rustToolchainInstalledOrUsed:false;nativeStudioExeBuilt:false;
  signedInstallerBuilt:false;gameFidelityProven:false;
  cleanIndependentWindowsInstallVerified:false;
  currentOwnerWitnessSignerAdmitted:false;
  totalGlobalHeavySlotsMax:3;singleWriterPerGame:true;
 };
};
const isObj=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
const eq=(a:Record<string,unknown>,b:Record<string,unknown>)=>
 Object.keys(a).sort().join("|")===Object.keys(b).sort().join("|") &&
 Object.entries(b).every(([k,v])=>a[k]===v);
const str=(s:unknown,l=400)=>typeof s==="string"&&s.length>5&&s.length<l;
const toolShas=[
 ["cl","fe251ef50a1545b1b0835ee17b1e785459712b38d79e45b5c1d3d28970a36619"],
 ["link","a364af801a8539e4324d9489313dbf001d959128451fc99a27b24676bbac058f"],
 ["sdk_signtool","431ee314c83988cacda86606356fd321b75ae0093481b97e3b738e99c412f2a0"]
];
function validateGate(g:unknown,i:number){
 if(!isObj(g)||g.id!==NATIVE_GATES[i]||!str(g.name,100)||
   !str(g.reason,500)||!str(g.prerequisites,400)||
   g.acceptedForProduction!==false)return false;
 const now=(i===1||i===2),old=i===2;
 return eq(Object.fromEntries(Object.entries(g).filter(([k])=>
  !["name","reason","prerequisites"].includes(k))),{
   id:NATIVE_GATES[i],readyHistorical:now,wasReadyInR23:old,acceptedForProduction:false
 });
}
function validateStep(s:unknown,i:number){
 if(!isObj(s) || s.id!==BUILD_STEPS[i] || !str(s.title,100) ||
   !str(s.needs,400) ||s.releaseAccepted!==false ||
   s.sourceStatus!==["MISSING","MISSING","BLOCKED","NOT_VERIFIED",
       "NOT_VERIFIED","NOT_AUTHORIZED","NOT_AUTHORIZED"][i])return false;
 return Object.keys(s).length===5;
}
export function validateNativeBuildReview(raw:unknown):raw is NativeBuildReport{
 if(!isObj(raw)||
   raw.schema!=="OpenRemaster.StudioNativeBuildReview.v1" ||
   raw.release!=="ORF-STUDIO-UI-20261018-r14" ||
   raw.status!=="REAL_MSVC_SYNTHETIC_SMOKE_SOURCE_PROVEN__TAURI_AND_OWNER_RELEASE_HOLD"||
   raw.authority!=="HISTORICAL_SAME_MACHINE_SOURCE_SHA_NOT_CURRENT_RELEASE_SIGNOFF"||
   raw.stage!=="OFFLINE_READONLY_TECHNICAL_EVIDENCE" ||
   typeof raw.generatedUtc!=="string"||!Number.isFinite(Date.parse(raw.generatedUtc)) ||
   !isObj(raw.sourcePins)||!eq(raw.sourcePins,NATIVE_SOURCE_PINS)||
   !Array.isArray(raw.gates)||raw.gates.length!==9||
   !raw.gates.every(validateGate)||
   !Array.isArray(raw.requiredSteps)||raw.requiredSteps.length!==7||
   !raw.requiredSteps.every(validateStep)||
   !isObj(raw.progress)||!isObj(raw.tooling)||!isObj(raw.pe)||
   !isObj(raw.production)||Object.keys(raw).length!==13)return false;
 const p=raw.progress;
 if(!eq(p,{
  historicalPriorReady:1,historicalNowReady:2,totalTechnicalGates:9,
  historicalRemaining:7,changedGate:"T02",
  syntheticExecutableProduced:true,syntheticExeSha256:SYNTHETIC_EXE_SHA,
  realStudioTauriAppProduced:false,prebuiltMicrosoftSDKProven:true,
  preinstalledMSVCCompilerProven:true,publisherApproved:false,
  approvedOriginalOrionIconLocated:false,independentOwnerA_B_CApproved:false,
  signedOneInstallerCreated:false,admittedProductionComponents:0
 }))return false;
 const t=raw.tooling;
 const tools=t.historicalSignedMicrosoftTools;
 if(!Array.isArray(tools)||tools.length!==3||!tools.every((tool,i)=>
  isObj(tool)&&eq(tool,{
    role:toolShas[i][0],sha256:toolShas[i][1],
    microsoftCodeSignatureValidAtR24:true,publisherIsOpenRemaster:false
  })))return false;
 const {historicalSignedMicrosoftTools,...otherTools}=t;
 if(!eq(otherTools,{
  msvcVersion:"14.44.35207",
  visualStudioVersion:"Enterprise 2022 17.14.42",
  sdkVersion:"10.0.26100.0",
  historicalR24SoftwareTests:19,newWin64ProcessExecutionByStudio:false,
  syntheticWin64SmokeActualExecutedAtR24:true,
  sourceOnlyReferenceNoExecutableCopied:true,syntheticExeIsNotStudioExe:true
 }))return false;
 if(!eq(raw.pe,{
  kind:"PE32_PLUS_CONSOLE_SYNTHETIC",amd64:true,aslr:true,
  highEntropyAslr:true,nxDep:true,sections:5,win64PointerBits:64,
  realTauriUiRendered:false
 }))return false;
 if(!eq(raw.production,{
  status:"HOLD_NO_AUTO_RETRY",mayInstall:false,mayDispatch:false,
  mayStartNativeWorker:false,mayAutoRetry:false,newSchedulerCreated:false,
  originalGamesOpenedOrModified:false,originalK003Modified:false,
  windowsAccountsServicesOrTasksModified:false,
  rustToolchainInstalledOrUsed:false,nativeStudioExeBuilt:false,
  signedInstallerBuilt:false,gameFidelityProven:false,
  cleanIndependentWindowsInstallVerified:false,
  currentOwnerWitnessSignerAdmitted:false,totalGlobalHeavySlotsMax:3,
  singleWriterPerGame:true
 }))return false;
 return true;
}
export function nativeBuildView(raw:unknown){
 return validateNativeBuildReview(raw)?
  {phase:"HISTORICAL_MSVC_SOURCE_ONLY" as const,data:raw}:
  {phase:"SOURCE_DRIFT_HOLD" as const,data:null};
}
export function simulateNativeBuild(report:NativeBuildReport,scenario:"actual"|"hypothetical"){
 return {
  scenario,
  acceptedProductionGates:0,
  historicalReadyGates:report.progress.historicalNowReady,
  hypotheticalRustAndIcon:(scenario==="hypothetical"),
  signedInstallerAvailable:false,
  nativeTauriStudioAvailable:false,
  canInstall:false,
  mayDispatch:false,
  status:"HOLD_NO_AUTO_RETRY" as const,
  explanation:scenario==="actual"
   ?"Two MSVC/SDK technical gates were observed in the historical r24 synthetic smoke."
   :"Only assumes approved Rust and original icon would become available; no real toolchain, native app, component closure, code signature, A/B/C or owner consent is established."
 };
}
